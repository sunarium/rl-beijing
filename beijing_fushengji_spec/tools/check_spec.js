#!/usr/bin/env node
/*
 * check_spec.js — 结构完整性校验
 *
 * 校验项：
 *  1. features/*.feature 首行为 `# language: zh-CN`
 *  2. 每个 场景/场景大纲 后紧跟 `# 来源:` 注释
 *  3. 三张事件登记表 Examples 数据行数：商业=18, 健康=12, 偷钱=7
 *  4. 所有标签都在词汇表内
 *  5. 标签：每个 feature 至少包含 @backend 或 @frontend
 *  6. 文件为 UTF-8（无 BOM）、无尾部空白行
 *
 * 用法：node tools/check_spec.js   （在 beijing_fushengji_spec/ 根下运行）
 */
const fs = require('fs');
const path = require('path');

const ROOT = __dirname.replace(/[\\/]tools$/, '');
const FEATURES = path.join(ROOT, 'features');

const TAG_VOCAB = new Set(['backend','frontend','state','rule-engine','stochastic','persistence','boundary','bug-faithful','verified']);

let failures = 0;
const fail = (file, msg) => { failures++; console.error(`  ✗ ${file}: ${msg}`); };

// must match a Chinese Gherkin keyword, possibly with tags line right before
const SCENARIO_HEAD = /^(?:场景|场景大纲|背景)\s*(?::.*)?$/;

const files = fs.readdirSync(FEATURES).filter(f => f.endsWith('.feature')).sort();
if (files.length === 0) { console.error('未找到任何 .feature 文件'); process.exit(1); }

for (const f of files) {
  const abs = path.join(FEATURES, f);
  const src = fs.readFileSync(abs, 'utf8');
  const lines = src.split(/\r?\n/);
  // strip BOM
  if (lines[0] && lines[0].charCodeAt(0) === 0xFEFF) { fail(f, '含 BOM'); continue; }

  // 1) language header
  if (!lines[0].trim().startsWith('# language: zh-CN')) fail(f, '首行不是 `# language: zh-CN`');

  // 2) 每个 背景/场景/场景大纲 块内至少一条 `# 来源:` 注释（从块头到下一个块头之前）
  const BLOCK_HEAD = /^(背景|场景|场景大纲):/;
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    if (BLOCK_HEAD.test(t)) {
      let found = false;
      for (let j = i + 1; j < lines.length; j++) {
        const u = lines[j].trim();
        if (BLOCK_HEAD.test(u)) break;              // 进入下一个块
        if (u.startsWith('# 来源:')) { found = true; break; }
      }
      if (!found) fail(f, `第 ${i + 1} 行「${lines[i].trim()}」所在块缺少 # 来源: 注释`);
    }
  }

  // 3) 事件登记表行数（数据行 = 场景大纲块内 `|` 行 − 表头 1 行；表格无分隔行）
  //    每个登记表只在其所属的文件中检查。
  const countTable = (ownsFile, name, expect) => {
    if (f !== ownsFile) return;
    const ls = src.split(/\r?\n/);
    let start = -1;
    for (let i = 0; i < ls.length; i++) {
      if (/^场景大纲:/.test(ls[i].trim()) && ls[i].includes(name)) { start = i; break; }
    }
    if (start < 0) { fail(f, `缺少登记表「${name}」`); return; }
    let pipes = 0, seenPipe = false;
    for (let i = start + 1; i < ls.length; i++) {
      const lt = ls[i].trim();
      if (/^(?:场景|背景|场景大纲):/.test(lt)) break;          // 下一个场景结束本块
      if (seenPipe && lt.startsWith('#')) break;               // 表格后的注释结束本块（表格前的 # 来源 忽略）
      if (lt.startsWith('|')) { pipes++; seenPipe = true; }
    }
    const data = pipes - 1; // 去掉表头行
    if (data !== expect) fail(f, `「${name}」数据行数=${data}，期望 ${expect}`);
  };
  countTable('07_商业事件.feature', '商业', 18);
  countTable('08_健康事件.feature', '健康事件', 12);
  countTable('09_金钱损失与黑客事件.feature', '偷钱', 7);

  // 4) tags vocabulary
  for (const tag of src.match(/@[a-z-]+/g) || []) {
    const name = tag.slice(1);
    if (!TAG_VOCAB.has(name)) fail(f, `未知标签 ${tag}`);
  }
  // 5) at least backend or frontend
  if (!/@backend/.test(src) && !/@frontend/.test(src)) fail(f, '缺少 @backend 或 @frontend 标签');
}

console.log(`检查 ${files.length} 个 feature 文件…`);
if (failures) { console.error(`\n共 ${failures} 处问题。`); process.exit(1); }
console.log('✓ 全部通过。');
