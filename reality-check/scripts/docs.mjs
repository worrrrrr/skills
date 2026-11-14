#!/usr/bin/env node
/**
 * docs.mjs — ดึงเอกสาร/ข้อมูลเวอร์ชันล่าสุดของ library หรือ API
 *
 * รูปแบบ:
 *   node docs.mjs <package|url> [options]
 *
 * ตัวอย่าง:
 *   node docs.mjs react
 *   node docs.mjs zod --grep schema
 *   node docs.mjs @tanstack/react-query --max 12000
 *   node docs.mjs requests --eco pypi
 *   node docs.mjs serde --eco crates
 *   node docs.mjs https://developers.cloudflare.com/workers/
 *
 * Options:
 *   --eco npm|pypi|crates   ระบบ package (default: auto)
 *   --max <chars>           งบตัวอักษรของเนื้อหา (default 6000)
 *   --grep <regex>          แสดงเฉพาะบรรทัดที่ตรง (ประหยัด context)
 *   --json                  คืนผลเป็น JSON
 *   --refresh               ไม่ใช้ cache
 *   -h, --help
 */

import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const UA = 'opencode-docs/1.0 (+local script)'
const CACHE_DIR = join(process.env.LOCALAPPDATA || process.env.XDG_CACHE_HOME || tmpdir(), 'opencode-docs-cache')
const TTL_HOURS = 12

// ---------------------------------------------------------------- args

function help() {
  console.log(`docs — latest library/API docs, trimmed for context

Usage:
  node docs.mjs <package|url> [options]

Options:
  --eco npm|pypi|crates   package ecosystem (default: auto)
  --max <chars>           content budget (default: 6000)
  --grep <regex>          only lines matching regex
  --json                  machine-readable output
  --refresh               bypass cache
  -h, --help

Examples:
  node docs.mjs react
  node docs.mjs zod --grep "schema"
  node docs.mjs requests --eco pypi
  node docs.mjs serde --eco crates
  node docs.mjs https://opencode.ai/docs/llms.txt`)
}

function die(msg) {
  console.error(`error: ${msg}`)
  process.exit(1)
}

function parseArgs(argv) {
  const opts = { eco: 'auto', max: 6000, json: false, refresh: false, grep: null }
  const targets = []
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--help' || a === '-h') { help(); process.exit(0) }
    else if (a === '--eco') opts.eco = String(argv[++i] || '').toLowerCase()
    else if (a === '--max') opts.max = Number(argv[++i])
    else if (a === '--grep') opts.grep = argv[++i]
    else if (a === '--json') opts.json = true
    else if (a === '--refresh') opts.refresh = true
    else if (a.startsWith('--')) die(`unknown option ${a} (try --help)`)
    else if (a.startsWith('-') && a.length > 1) die(`unknown option ${a} (try --help)`)
    else targets.push(a)
  }
  if (!Number.isFinite(opts.max) || opts.max < 200) opts.max = 6000
  if (!targets.length) { help(); process.exit(0) }
  return { opts, targets }
}

// ---------------------------------------------------------------- http + cache

const sha = (s) => createHash('sha1').update(s).digest('hex')

async function fetchCached(url, opts, ttlHours = TTL_HOURS) {
  const file = join(CACHE_DIR, sha(url) + '.json')
  if (!opts.refresh) {
    try {
      const c = JSON.parse(await readFile(file, 'utf8'))
      if (Date.now() - c.ts < ttlHours * 3600_000) return c
    } catch { /* miss */ }
  }
  let entry
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      headers: { 'user-agent': UA, accept: 'text/html,application/json,text/plain,text/markdown,*/*' },
      signal: AbortSignal.timeout(20_000),
    })
    entry = {
      ts: Date.now(),
      status: res.status,
      finalUrl: res.url || url,
      type: (res.headers.get('content-type') || '').toLowerCase(),
      body: await res.text(),
    }
  } catch (err) {
    entry = { ts: Date.now(), status: 0, finalUrl: url, type: '', body: '', error: String(err?.message || err) }
  }
  try { await mkdir(CACHE_DIR, { recursive: true }); await writeFile(file, JSON.stringify(entry)) } catch { /* ignore */ }
  return entry
}

const okStatus = (r) => r.status >= 200 && r.status < 300

function looksLikeHtml(text) {
  const head = text.slice(0, 400).toLowerCase()
  return head.includes('<!doctype html') || head.includes('<html') || head.includes('<head')
}

async function getText(url, opts) {
  const r = await fetchCached(url, opts)
  if (!okStatus(r) || !r.body || looksLikeHtml(r.body)) return null
  return r
}

async function getJson(url, opts) {
  const r = await fetchCached(url, opts)
  if (!okStatus(r)) return null
  try { return JSON.parse(r.body) } catch { return null }
}

// ---------------------------------------------------------------- html → text

const ENTITIES = {
  amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', hellip: '…', mdash: '—', ndash: '–',
  lsquo: '‘', rsquo: '’', ldquo: '“', rdquo: '”', copy: '©', reg: '®', trade: '™', middot: '·', bull: '•',
}

function decodeEntities(s) {
  return s
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => safeChar(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => safeChar(parseInt(d, 10)))
    .replace(/&([a-z][a-z0-9]+);/gi, (m, n) => ENTITIES[n.toLowerCase()] ?? m)
}

function safeChar(code) {
  try { return String.fromCodePoint(code) } catch { return '' }
}

function htmlToText(html) {
  let s = html
  s = s.replace(/<script\b[\s\S]*?<\/script>/gi, ' ')
  s = s.replace(/<style\b[\s\S]*?<\/style>/gi, ' ')
  s = s.replace(/<noscript\b[\s\S]*?<\/noscript>/gi, ' ')
  s = s.replace(/<svg\b[\s\S]*?<\/svg>/gi, ' ')
  s = s.replace(/<!--[\s\S]*?-->/g, ' ')

  const main = s.match(/<main\b[\s\S]*?<\/main>/i) || s.match(/<article\b[\s\S]*?<\/article>/i)
  if (main) s = main[0]

  s = s.replace(/<h([1-6])[^>]*>/gi, (_, n) => '\n\n' + '#'.repeat(Number(n)) + ' ')
  s = s.replace(/<li[^>]*>/gi, '\n- ')
  s = s.replace(/<br\s*\/?>/gi, '\n')
  s = s.replace(/<\/(p|div|section|article|tr|ul|ol|table|blockquote|pre|h[1-6])>/gi, '\n')
  s = s.replace(/<td[^>]*>/gi, ' | ')
  s = s.replace(/<[^>]+>/g, '')
  s = decodeEntities(s)
  s = s.replace(/[ \t]+\n/g, '\n')
  s = s.replace(/\n{3,}/g, '\n\n')
  s = s.replace(/[ \t]{2,}/g, ' ')
  return s.trim()
}

// ---------------------------------------------------------------- registries

function normalizeRepo(url) {
  if (!url || typeof url !== 'string') return null
  return url
    .replace(/^git\+/, '')
    .replace(/^git:\/\//, 'https://')
    .replace(/^ssh:\/\/git@/, 'https://')
    .replace(/^git@([^:]+):/, 'https://$1/')
    .replace(/\.git$/, '')
    .replace(/\/+$/, '')
}

async function npmInfo(name, opts) {
  const spec = name.startsWith('@') ? name.replace('/', '%2F') : encodeURIComponent(name)
  const d = await getJson(`https://registry.npmjs.org/${spec}/latest`, opts)
  if (!d) return null
  return {
    ecosystem: 'npm', name: d.name || name, version: d.version,
    description: d.description, license: d.license,
    homepage: d.homepage || null,
    repository: normalizeRepo(typeof d.repository === 'string' ? d.repository : d.repository?.url),
  }
}

async function pypiInfo(name, opts) {
  const d = await getJson(`https://pypi.org/pypi/${encodeURIComponent(name)}/json`, opts)
  if (!d?.info) return null
  const info = d.info
  const urls = info.project_urls || {}
  const pick = (...keys) => keys.map((k) => urls[k]).find(Boolean) || null
  return {
    ecosystem: 'pypi', name: info.name, version: info.version,
    description: info.summary, license: info.license,
    homepage: info.home_page || pick('Homepage', 'Home', 'Website'),
    repository: normalizeRepo(pick('Source', 'Source Code', 'Repository', 'Code', 'GitHub')),
    documentation: pick('Documentation', 'Docs', 'Documentation URL'),
  }
}

async function cratesInfo(name, opts) {
  const d = await getJson(`https://crates.io/api/v1/crates/${encodeURIComponent(name)}`, opts)
  if (!d?.crate) return null
  const c = d.crate
  return {
    ecosystem: 'crates', name: c.name, version: c.max_version,
    description: c.description, license: null,
    homepage: c.homepage || null,
    repository: normalizeRepo(c.repository),
    documentation: c.documentation || null,
  }
}

async function resolvePackage(name, opts) {
  const order = opts.eco === 'auto' ? ['npm', 'pypi', 'crates'] : [opts.eco]
  const fns = { npm: npmInfo, pypi: pypiInfo, crates: cratesInfo }
  for (const eco of order) {
    const fn = fns[eco]
    if (!fn) die(`unsupported --eco ${eco} (use npm, pypi or crates)`)
    const info = await fn(name, opts)
    if (info) return info
  }
  return null
}

// ---------------------------------------------------------------- doc sources

const isGitHub = (u) => /^https:\/\/github\.com\/[^/]+\/[^/]+/i.test(u || '')

function originsFor(info) {
  const out = new Set()
  for (const u of [info.homepage, info.documentation]) {
    if (!u || !/^https?:/i.test(u)) continue
    try { out.add(new URL(u).origin) } catch { /* skip */ }
  }
  return [...out]
}

async function findLlms(pkg, opts) {
  for (const origin of originsFor(pkg)) {
    for (const path of ['/llms.txt', '/docs/llms.txt']) {
      const url = origin + path
      const r = await getText(url, opts)
      if (r && r.body.length > 20) return { url: r.finalUrl, body: r.body, kind: 'llms.txt' }
    }
  }
  return null
}

async function findReadme(pkg, opts) {
  const repo = pkg.repository
  if (!isGitHub(repo)) return null
  for (const branch of ['HEAD', 'main', 'master']) {
    for (const file of ['README.md', 'readme.md', 'README.markdown']) {
      const url = `https://raw.githubusercontent.com/${repo.replace('https://github.com/', '')}/${branch}/${file}`
      const r = await getText(url, opts)
      if (r && r.body.length > 50) return { url: r.finalUrl, body: r.body, kind: 'readme' }
    }
  }
  return null
}

async function findPage(pkg, opts) {
  for (const url of [pkg.homepage, pkg.documentation]) {
    if (!url || !/^https?:/i.test(url)) continue
    const r = await fetchCached(url, opts)
    if (!okStatus(r) || !r.body) continue
    return { url: r.finalUrl, body: htmlToText(r.body), kind: 'page' }
  }
  return null
}

async function fetchUrlDoc(url, opts) {
  const r = await fetchCached(url, opts)
  if (!okStatus(r)) return null
  const body = looksLikeHtml(r.body) ? htmlToText(r.body) : r.body
  if (!body.trim()) return null
  return { url: r.finalUrl, body, kind: looksLikeHtml(r.body) ? 'page' : 'text' }
}

// ---------------------------------------------------------------- output

function truncate(text, max) {
  if (text.length <= max) return text
  const cut = text.slice(0, max)
  const lastBreak = cut.lastIndexOf('\n')
  const body = lastBreak > max * 0.7 ? cut.slice(0, lastBreak) : cut
  return `${body}\n\n… [truncated ${text.length - body.length} chars; raise with --max ${Math.min(30_000, max * 2)}]`
}

function applyGrep(text, pattern) {
  let re
  try { re = new RegExp(pattern, 'i') } catch { die(`invalid --grep regex: ${pattern}`) }
  const lines = text.split('\n')
  const hits = lines.filter((l) => re.test(l))
  if (!hits.length) return `(no lines matching /${pattern}/i)`
  return `${hits.join('\n')}\n\n[match: ${hits.length}/${lines.length} lines]`
}

function printReadable(meta, doc, opts) {
  const out = []
  out.push(`${meta.name}@${meta.version}  (${meta.ecosystem})`)
  if (meta.description) out.push(`desc   : ${String(meta.description).replace(/\s+/g, ' ').slice(0, 300)}`)
  if (meta.license) out.push(`license: ${meta.license}`)
  if (meta.repository) out.push(`repo   : ${meta.repository}`)
  if (meta.homepage) out.push(`home   : ${meta.homepage}`)
  if (meta.documentation) out.push(`docs   : ${meta.documentation}`)
  out.push(`source : ${doc.url}  [${doc.kind}]`)

  let content = doc.body
  if (opts.grep) content = applyGrep(content, opts.grep)
  content = truncate(content, opts.max)

  console.log(out.join('\n'))
  console.log('---')
  console.log(content)
}

function printUrl(meta, doc, opts) {
  let content = doc.body
  if (opts.grep) content = applyGrep(content, opts.grep)
  content = truncate(content, opts.max)
  console.log(`${meta.name}  [${doc.kind}]`)
  console.log(`source : ${doc.url}`)
  console.log('---')
  console.log(content)
}

// ---------------------------------------------------------------- main

async function main() {
  const { opts, targets } = parseArgs(process.argv.slice(2))
  const target = targets[0]

  if (/^https?:\/\//i.test(target)) {
    const doc = await fetchUrlDoc(target, opts)
    if (!doc) die(`could not fetch ${target}`)
    if (opts.json) return console.log(JSON.stringify({ url: doc.url, kind: doc.kind, content: truncate(doc.body, opts.max) }, null, 2))
    return printUrl({ name: new URL(target).host }, doc, opts)
  }

  const pkg = await resolvePackage(target, opts)
  if (!pkg) die(`package not found: ${target} (try --eco npm|pypi|crates)`)

  const doc = (await findLlms(pkg, opts)) || (await findReadme(pkg, opts)) || (await findPage(pkg, opts))
  if (!doc) {
    console.log(`${pkg.name}@${pkg.version}  (${pkg.ecosystem})`)
    if (pkg.repository) console.log(`repo   : ${pkg.repository}`)
    die('no docs source found (no llms.txt / README / homepage)')
  }

  if (opts.json) {
    return console.log(JSON.stringify({ ...pkg, source: doc.url, kind: doc.kind, content: truncate(doc.body, opts.max) }, null, 2))
  }
  printReadable(pkg, doc, opts)
}

main().catch((err) => die(err?.stack || String(err)))
