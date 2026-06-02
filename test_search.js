// Қидирув функцияларининг автоматик тести. index.html дан соф функцияларни
// ажратиб (DOM керак эмас) ҳар бир талаб бўйича текширади.
//   node test_search.js
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('index.html', 'utf8');

// escHtml сатрини ажратамиз
const escLine = html.slice(html.indexOf('function escHtml'));
const escHtmlSrc = escLine.slice(0, escLine.indexOf('\n'));

// Нормализация/highlight тўпламини ажратамиз
const start = html.indexOf('const _CYR = {');
const end = html.indexOf('function isArabicQuery');
if (start < 0 || end < 0) { console.error('FATAL: toolkit block not found'); process.exit(1); }
const block = html.slice(start, end);

const src = escHtmlSrc + '\n' + block + '\n' +
  '({normUz,normArab,buildNormMap,firstMatch,allMatches,renderSnippet,normArabKeep,_hasHarakat});';
const F = vm.runInNewContext(src, {});

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra ? '  → ' + extra : '')); }
}
function section(t){ console.log('\n' + t); }

const { normUz, normArab, firstMatch, allMatches, renderSnippet, normArabKeep, _hasHarakat } = F;
const fm = (text, q, ar) => firstMatch(ar ? normArab(text) : normUz(text), ar ? normArab(q) : normUz(q), !!ar);

// 1. Кўп ёзувли — кирилл ва лотин бир хил калит/натижа
section('1. Кўп ёзувли (кирилл ↔ лотин)');
ok('normUz("ҳаққ") === normUz("haqq")', normUz('ҳаққ') === normUz('haqq'), normUz('ҳаққ') + ' / ' + normUz('haqq'));
ok('normUz("ўзбек") === normUz("o\'zbek")', normUz('ўзбек') === normUz("o'zbek"), normUz('ўзбек') + ' / ' + normUz("o'zbek"));
ok('normUz("ШАРҲ") === normUz("sharh")', normUz('ШАРҲ') === normUz('sharh'), normUz('ШАРҲ'));
ok('лотинча сўров кириллни топади', fm('Аллоҳнинг ҳаққи', 'haqq') !== -1);
ok('кириллча сўров кириллни топади', fm('Аллоҳнинг ҳаққи', 'ҳаққ') !== -1);

// 2. Сўз чегараси
section('2. Сўз чегараси (word-boundary)');
ok('«ҳаққ» → «ҳаққи» топади', fm('ҳаққи берилди', 'ҳаққ') !== -1);
ok('«ҳаққ» → «ҳаққингизни» топади', fm('ҳаққингизни олинг', 'ҳаққ') !== -1);
ok('«ҳаққ» → «муҳаққақки» ТОПМАЙДИ', fm('муҳаққақки шундай', 'ҳаққ') === -1);
ok('сўз ўртаси топилмайди (latin)', fm('муҳаққақки', 'haqq') === -1);
ok('бошланғич мослик (idx=0)', firstMatch(normUz('ҳаққи'), normUz('ҳаққ')) === 0);

// 3. Highlight асл матнга тўғри (позиция-харита)
section('3. Highlight — позиция-харита (асл матн)');
{
  const out = renderSnippet('Аллоҳнинг ҳаққи бор', normUz('ҳаққ'), 'uz', 9999);
  ok('асл «ҳаққ» ажратилди', out.includes('<mark>ҳаққ</mark>'), out);
  ok('асл матн ҳарфлари сақланди', out.includes('Аллоҳнинг') && out.includes('бор'), out);
}
{
  // Лотин сўров, кирилл матн — mark асл кириллга тушсин
  const out = renderSnippet('Бу ҳаққи рост', normUz('haqq'), 'uz', 9999);
  ok('лотин сўровда асл кирилл ажратилди', out.includes('<mark>ҳаққ</mark>'), out);
}
{
  // Бир неча мослик
  const out = renderSnippet('ҳаққи ва ҳаққи', normUz('ҳаққ'), 'uz', 9999);
  ok('барча мосликлар ажратилди', (out.match(/<mark>/g) || []).length === 2, out);
}

// 4. Парча — топилган сўз доим кўринади
section('4. Парча (snippet windowing)');
{
  const long = 'А'.repeat(300) + ' ҳаққи ' + 'Б'.repeat(300);
  const out = renderSnippet(long, normUz('ҳаққ'), 'uz', 200);
  ok('узун матн қисқартирилди', out.length < long.length);
  ok('топилган сўз кўринади', out.includes('<mark>ҳаққ</mark>'), out.slice(0, 80));
  ok('боши … билан', out.startsWith('…'));
  ok('охири … билан', out.endsWith('…'));
}

// 5. Кечиримли арабча
section('5. Арабча — кечиримли (ҳаракат / артикл)');
{
  const VOW = 'الْحَمْدُ لِلَّهِ';   // ҳаракатли асл
  ok('ҳаракатсиз сўров ҳаракатли матнни топади', fm(VOW, 'حمد', true) !== -1);
  ok('«ал» артикли ихтиёрий («حمد» → «الحمد»)', firstMatch(normArab(VOW), normArab('حمد'), true) !== -1);
  ok('артикл билан ҳам топади', fm(VOW, 'الحمد', true) !== -1);
  const out = renderSnippet(VOW, normArab('حمد'), 'ar', 9999);
  ok('арабча highlight асл ҳаракатли матнга тушди', out.includes('<mark>') && /[ً-ْ]/.test(out), out);
  ok('ҳаракат сўров аниқланди', _hasHarakat('حَمد') === true && _hasHarakat('حمد') === false);
  ok('normArabKeep ҳаракатни сақлайди', /[ً-ْ]/.test(normArabKeep('حَمد')));
}

// 6. Яширин қисмлар (footnote / izoh)
section('6. Яширин қисмлар (footnote ичида)');
{
  const matn = 'Асосий матн бу ерда.\n\n* изоҳ: хамийла маъноси.';
  ok('footnote сўзи топилади', fm(matn, 'хамийла') !== -1);
  const out = renderSnippet(matn, normUz('хамийла'), 'uz', 40);
  ok('парча footnote сўзини кўрсатади', out.includes('<mark>хамийла</mark>'), out);
}

// 7. Рақам / passthrough
section('7. Рақам ва махсус белгилар');
ok('рақамлар ўзгармайди', normUz('294') === '294');
ok('бўш сўров мослик бермайди', firstMatch(normUz('матн'), normUz('')) === -1);

// 8. XSS — HTML бузилмайди
section('8. XSS хавфсизлиги');
{
  const out = renderSnippet('<script>alert(1)</script> ҳаққи', normUz('ҳаққ'), 'uz', 9999);
  ok('тег escape қилинди', out.includes('&lt;script&gt;'), out.slice(0, 60));
  ok('хом <script> йўқ', !out.includes('<script>'));
  ok('mark тўғри ишлайди', out.includes('<mark>ҳаққ</mark>'));
}

console.log('\n──────────────────────────────');
console.log(`Натижа: ${pass} ✓   ${fail} ✗`);
process.exit(fail ? 1 : 0);
