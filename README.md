
<div align="center">

<img src="buxoriy.JPG" width="140" alt="Buxoriy">

# Имом Бухорий «Саҳиҳ» тўплами — ўзбекча таржима

**«Ал-Жомиъ ас-Саҳиҳ» ҳадислар тўпламининг тўлиқ ўзбекча таржимаси — битта саҳифали ўқув иловари (PWA)**

[**📖 Ўқишни бошлаш → abuyahyo.github.io/buxoriy**](https://abuyahyo.github.io/buxoriy/)

<sub>98 китоб · 7,558 ҳадис · ҳаммаси таржимали · арабча матн · офлайн</sub>

</div>

---

## ✨ Имкониятлар

### 📖 Мазмун
- **7,558 ҳадис** — Имом Бухорийнинг «Ал-Жомиъ ас-Саҳиҳ» тўпламининг тўлиқ ўзбекча таржимаси
- **98 китоб** — китоб → боб → ҳадис тартибида уч босқичли навигация
- **Арабча матн** — ҳар бир ҳадисдаги «Арабча» тугмаси орқали тоза иснод ва матн (7,558/7,558 — 100%), RTL ва Amiri/Noto Naskh Arabic шрифтларида
- **Изоҳ, ровий ва манба** — ба'зи ҳадисларда учраган батафсил шарҳлар сақланиб қолган
- **Олтин Силсила таржимаси** — Шайх Муҳаммад Содиқ Муҳаммад Юсуф раҳбарлигидаги жамоа таржимаси билан бойитилган

### 🔍 Қидирув
- Ўзбекча матн бўйича тезкор қидирув

### 🌐 Арабча сайт
- `ar/` папкасида — **бутунлай арабча алоҳида сайт**: ўз `index.html`, `data.json` ва `sw.js`ига эга, китоб → боб → ҳадис навигацияси ва hash-routing (`#k/1/b/2/h/3`) билан

### 📱 PWA
- **Офлайн ишлайди** — бир марта очилгач интернет керак эмас
- **Янгиланиш банери** — янги версия чоп этилганда фойдаланувчига кўринади
- Телефон бош экранига қўшилади

---

## 🚀 Ишга тушириш

```bash
git clone https://github.com/abuyahyo/buxoriy.git
cd buxoriy
python3 -m http.server 8765
# Браузерда: http://127.0.0.1:8765
```

Ҳеч қандай қуриш (build) талаб қилинмайди — браузерда ёки оддий статик серверда очилади.

> Бош саҳифа дарҳол кўринади: китоблар рўйхати HTML ичида inline сақланади; `index.json` (~2.5 MB) параллель юкланади, `data.json` (~10.9 MB) орқа фондан.

---

## ⚙️ Маълумотларни қайта қуриш

`data.json` бутун `sahihul-buxoriy.txt` манба файлидан генерация қилинган:

```bash
python3 build_from_txt.py   # sahihul-buxoriy.txt -> data.json
python3 build_index.py      # index.json + inline BOOKS + sw.js кеш версияси
```

> ⚠️ `data.json` ўзгаргач албатта `build_index.py` ишга туширилади — акс ҳолда бош саҳифа ва Service Worker кеши эски қолади.

Батафсил қуриш жараёни ва арабча матнни тўлдириш скриптлари `CLAUDE.md` да баён этилган.

---

## 🗂 Лойиҳа тузилиши (асосий файллар)

| Файл | Вазифаси |
|------|----------|
| `index.html` | Бир-файлли ўзбекча илова (HTML + CSS + JS) |
| `data.json` | Барча китоб/боб/ҳадислар (~10.9 MB, 7,558 ҳадис) |
| `arabic.json` | Ҳар ҳадиснинг тоза арабча иснод+матни (~3.7 MB, lazy юкланади) |
| `index.json` | Китоб/боб метамаълумоти (~2.5 MB) |
| `sw.js`, `manifest.json` | PWA: офлайн ва янгиланиш бошқаруи |
| `ar/` | Тўлиқ арабча алоҳида сайт (ўз `index.html`, `data.json`, `sw.js`) |
| Python скриптлар | Манбадан қайта қуриш ва таржима интеграцияси воситалари |

---

## 📦 Тарқатиш (Deploy)

- Ўзбекча: [abuyahyo.github.io/buxoriy](https://abuyahyo.github.io/buxoriy/)
- Арабча: [abuyahyo.github.io/buxoriy/ar](https://abuyahyo.github.io/buxoriy/ar/)

GitHub Pages `main` тармоғидан автоматик тарқатади.

---

## 🤝 Ҳисса қўшиш

Таржимадаги хатоликни топсангиз — [Issue](https://github.com/abuyahyo/buxoriy/issues) очинг. Матн тузатишлар манба нашрга аниқ мос қилиб қилинади.

---

<div align="center">
<sub>Аллоҳ бу амални қабул қилсин ва ўқувчиларга манфаат берсин. 🤲</sub>
</div>

---

## 🇬🇧 English

<div align="center">

# Sahih al-Bukhari — Uzbek Translation Reader

A single-page PWA with the complete Uzbek translation of Imam al-Bukhari's «Al-Jami' as-Sahih» — **7,558 hadiths across 98 books**, plus a fully separate Arabic-language edition.

[**Open the reader**](https://abuyahyo.github.io/buxoriy/) · [**Arabic edition**](https://abuyahyo.github.io/buxoriy/ar/)

</div>

### Features
- **Complete translation** — all 7,558 hadiths translated; three-level navigation (book → chapter → hadith)
- **Original Arabic** — every hadith has clean isnad + matn in Arabic (100% coverage), lazy-loaded on demand, rendered RTL with Amiri/Noto Naskh Arabic
- **Golden Silsila translation** — enriched with the team translation led by Shaykh Muhammad Sodiq Muhammad Yusuf
- **PWA** — offline support, update banner, installable

### Architecture
Three-stage loading keeps the home page instant: inline book list (~10 KB) → `index.json` (~2.5 MB, preloaded in parallel) → `data.json` (~10.9 MB, prefetched in background). Arabic texts live separately in `arabic.json` (~3.7 MB) and are fetched only when the reader opens a hadith.

| File | Purpose |
|------|---------|
| `index.html` | Single-file Uzbek app (HTML + CSS + JS) |
| `data.json` | All books/chapters/hadiths (~10.9 MB) |
| `arabic.json` | Arabic isnad + matn per hadith (lazy) |
| `index.json` | Book/chapter metadata |
| `ar/` | Fully separate Arabic site |
| Python scripts | Rebuild pipeline (`build_from_txt.py`, `build_index.py`, …) |

### Rebuild data
```bash
python3 build_from_txt.py   # source text -> data.json
python3 build_index.py      # index.json + inline books + SW cache bump
```

> Run `build_index.py` after every `data.json` change, otherwise the home page and the service-worker cache go stale.

### Deploy
Served automatically from `main` via GitHub Pages.
