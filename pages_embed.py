"""The "Embed this calculator" page: iframe code for the calculators that have a bare embed copy (calcs_common.EMBEDS)."""
from html import escape as e

import calcs_common as c

HOME_CARDS = [("embed/index.html", "For your site", "Embed a calculator", "Free iframe code for your blog or shop. No sign-up.", "")]
FEATURED = ["concrete-slab", "roof-pitch", "mead-abv", "ec-ppm"]  # shown with a live preview; the rest as code only


def snippet(name, title, path, height, sub="", credit="Calculator:"):
    # The line under the frame sits on the host page itself, so it is a link from that site to this one. Google's
    # guidance treats keyword-rich, followed links in widgets as a link scheme: the anchor is the brand only and the
    # link is nofollow. The mention of the brand is what the widget is for, not the link weight.
    return (f'<iframe src="{c.B.BASE}/embed/{sub}{name}.html" title="{e(title)}" width="100%" height="{height}" '
            f'style="border:0;max-width:720px" loading="lazy"></iframe>\n'
            f'<p style="font-size:14px;margin:6px 0 0">{credit} <a href="{c.B.BASE}/{path}" rel="nofollow">'
            f'{e(c.B.CFG["brand"])} Tools</a></p>')


def alternates():
    """The English and the Ukrainian embed page are the same page in two languages (hreflang)."""
    return [("en", f"{c.B.BASE}/embed/"), ("uk", f"{c.B.BASE}/embed/uk/"), ("x-default", f"{c.B.BASE}/embed/")]


def build():
    items = sorted(c.EMBEDS, key=lambda x: (x[0] not in FEATURED, FEATURED.index(x[0]) if x[0] in FEATURED else 0, x[1]))
    blocks = []
    for name, title, path, height in items:
        code = snippet(name, title, path, height)
        preview = (f'<iframe src="{{rel}}embed/{name}.html" title="{e(title)} preview" height="{height}" loading="lazy"></iframe>'
                   if name in FEATURED else "")
        blocks.append(f'<div class="embed-item"><h3>{e(title)}</h3><p class="muted">Full page: <a href="{{rel}}{path}">{e(title)}</a></p>'
                      f'<textarea class="embed-code" readonly rows="6" aria-label="Embed code for {e(title)}">{e(code)}</textarea>{preview}</div>')
    faq_html, faq_ld = c.B.faq([
        ("Is it free? Do I need an account?",
         "Free, with no sign-up and no key. Copy the code and paste it into your page."),
        ("What does the embedded calculator show?",
         "Only the calculator, with a small \"Powered by Dre Dev Tools\" line, and under the frame one line of text with a link to the full page with the charts and sources. No ads, no cookies and no analytics inside the frame."),
        ("Can I change the size?",
         "Yes. The width follows your page up to 720 px. If the calculator is cut off or leaves a gap on your layout, change the height number in the code."),
        ("Will the numbers stay up to date?",
         "Yes. The frame loads the calculator from this site, so fixes and updates reach your page without any change on your side."),
        ("Which platforms does it work on?",
         "Anywhere you can paste HTML: WordPress (Custom HTML block), Squarespace (Code block), Wix (Embed HTML), Shopify pages and plain HTML sites."),
    ])
    body = f"""
{c.CSS}
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › Embed</div>
<div class="hero"><div class="eyebrow">For blogs, shops and course sites</div><h1>Embed this calculator</h1>
<p class="lead">Put one of our calculators on your own site with a short piece of code. Free, no sign-up, no ads inside the frame.</p></div>
<section class="prose"><h2>How to add it</h2>
<ol><li>Pick a calculator below and copy its code.</li>
<li>Paste it into your page where the calculator should appear (an HTML or code block in your site builder).</li>
<li>Publish. If it looks cut off, change the <code>height</code> number.</li></ol>
<p>The code has two parts: the calculator itself and one line under it, "Calculator: Dre Dev Tools", that links to the full page with the charts and sources. Please keep both as they are. The link carries <code>rel="nofollow"</code>, so it passes no ranking credit and is safe under search engines' rules for widget links.</p>
<p lang="uk">Віджети українською (час роботи від АКБ, переріз кабелю до інвертора, падіння напруги): <a href="{{rel}}embed/uk/" hreflang="uk">вбудувати калькулятор українською</a>.</p></section>
<section class="prose"><h2>Terms, in plain words</h2>
<ul><li>Free for any site, a shop or a paid course included. No sign-up, no key, no limit on page views.</li>
<li>Keep the "Calculator: Dre Dev Tools" line with its link under the frame. That line is the only thing asked in return.</li>
<li>Do not change the calculator, hide the "Powered by" line or present it as your own tool.</li>
<li>The calculators are reference tools: the limits on the <a href="{{rel}}methodology.html">methodology page</a> apply on your site as well.</li>
<li>A calculator may be updated when a number is corrected; corrections are listed in the <a href="{{rel}}changelog.html">changelog</a>. If one ever has to be withdrawn, its address will keep answering with a link to the full page.</li></ul>
<p>The superheat calculator can open on one refrigerant: add it after a # sign in the frame address, for example <code>superheat-subcooling.html#r-454b</code>.</p></section>
<section><h2>Calculators you can embed</h2>{"".join(blocks)}</section>
{faq_html}
<p class="note">Questions or a calculator you would like to embed that is not here: <a href="mailto:{c.B.CFG["support_email"]}">{c.B.CFG["support_email"]}</a>.</p>
"""
    c.B.shell("embed/index.html", "Embed a Free Calculator on Your Site (iframe code) | Dre Dev Tools",
              "Free embeddable calculators for your blog, shop or course: concrete slab, candle wax, soap lye, voltage drop, superheat and more. Copy the iframe code, no sign-up.",
              body, "", "embed", [faq_ld], c.scripts(), alternates=alternates())
    build_uk()


# ---------- Ukrainian widgets: /embed/uk/ ----------
# For battery and inverter shops, OSBB (condo) sites and blogs during the blackout season. The battery card is the one
# on electrical/uk/battery-runtime.html (pages_electrical.UK_CARDS); voltage drop and the inverter cable run on
# assets/embed-uk.js, which uses calc.js's IEC constants and the Electrician Calc app's IEC 60364-5-52 table.

VD_UK_CARD = """<div class="calc card">
<div class="fields">
<div class="full"><div class="seg" id="supply" role="group" aria-label="Мережа">
<button data-v="single" aria-pressed="true">1 фаза</button><button data-v="three" aria-pressed="false">3 фази</button><button data-v="dc" aria-pressed="false">Постійний струм</button></div></div>
<div class="full"><div class="seg" id="cond" role="group" aria-label="Провідник">
<button data-v="cu" aria-pressed="true">Мідь</button><button data-v="al" aria-pressed="false">Алюміній</button></div></div>
<div><label for="size">Переріз жили</label><select id="size"></select></div>
<div><label for="len">Довжина <small>(м, в один бік)</small></label><input id="len" inputmode="decimal" value="30"></div>
<div><label for="amps">Струм навантаження <small>(А)</small></label><input id="amps" inputmode="decimal" value="16"></div>
<div><label for="volts">Напруга <small>(В)</small></label><input id="volts" inputmode="decimal" value="230"></div>
<div class="full"><label for="pf">Коефіцієнт потужності <small>(1 для нагрівачів і ламп, ~0,85 для двигунів)</small></label><input id="pf" inputmode="decimal" value="1"></div>
</div>
<div class="result" aria-live="polite">
<div class="eyebrow">Падіння напруги</div>
<div class="big" id="vd-pct">–</div>
<div class="rows">
<div><span>Падіння</span><span id="vd-v">–</span></div>
<div><span>Напруга на навантаженні</span><span id="vd-end">–</span></div>
<div><span>Найменший переріз для ≤ 3 %</span><span id="vd-min">–</span></div>
</div>
<div id="vd-verdict" class="verdict"></div>
<p class="note">Лише падіння напруги. Переріз за допустимим струмом і автомат треба перевірити окремо.</p>
</div>
</div>"""

CABLE_UK_CARD = """<div class="calc card"><div class="fields">
<div class="full"><label>Напруга банку АКБ</label>
<div class="seg" id="ic-vpre" role="group" aria-label="Типові напруги"><button data-v="12" aria-pressed="true">12 В</button><button data-v="24" aria-pressed="false">24 В</button><button data-v="48" aria-pressed="false">48 В</button></div></div>
<div><label for="ic-v">Напруга <small>(В)</small></label><input id="ic-v" inputmode="decimal" value="12"></div>
<div><label for="ic-w">Потужність інвертора <small>(Вт, найбільше навантаження)</small></label><input id="ic-w" inputmode="decimal" value="1000"></div>
<div><label for="ic-eff">ККД інвертора <small>(%)</small></label><input id="ic-eff" inputmode="decimal" value="85"></div>
<div><label for="ic-len">Довжина кабелю <small>(м, в один бік)</small></label><input id="ic-len" inputmode="decimal" value="1.5"></div>
<div class="full"><label>Допустиме падіння напруги</label><div class="seg" id="ic-limit" role="group" aria-label="Допустиме падіння напруги"><button data-v="1" aria-pressed="false">1 %</button><button data-v="2" aria-pressed="true">2 %</button><button data-v="3" aria-pressed="false">3 %</button></div></div>
</div><div class="result" aria-live="polite"><div class="eyebrow">Переріз кабелю</div><div class="big" id="ic-size">–</div>
<div class="rows"><div><span>Струм з АКБ</span><span id="ic-amps">–</span></div>
<div><span id="ic-limit-label">Найменший переріз для падіння ≤ 2 %</span><span id="ic-bydrop">–</span></div>
<div><span>Найменший переріз за струмом (IEC 60364-5-52, B.52.2, метод C)</span><span id="ic-byamps">–</span></div>
<div><span>Падіння напруги</span><span id="ic-drop">–</span></div>
<div><span>Втрати в кабелі</span><span id="ic-loss">–</span></div></div>
<div id="ic-verdict" class="verdict"></div>
<p class="note">Мідь, ізоляція ПВХ 70 °C, повітря 30 °C. Запобіжник між АКБ і інвертором, нагрів у пучку і пускові струми не перевіряються.</p></div></div>"""

# (name, title, full page, iframe height measured at 720 px plus a margin, line for the embed page)
UK_EMBEDS = [
    ("battery-runtime", "На скільки вистачить акумулятора або ДБЖ", "electrical/uk/battery-runtime.html", 1600,
     "Години роботи від АКБ через інвертор, час заряду і потрібна ємність банку. Для магазинів АКБ та інверторів, ОСББ і блогів про резервне живлення."),
    ("inverter-cable", "Переріз кабелю від АКБ до інвертора", "electrical/dc-wire-size-calculator.html", 1000,
     "Струм з АКБ, переріз за падінням напруги і за допустимим струмом (IEC 60364-5-52), втрати в кабелі. Мідь, 12, 24 або 48 В."),
    ("voltage-drop", "Калькулятор падіння напруги", "electrical/voltage-drop-calculator.html", 940,
     "Мідь або алюміній, мм², 1 чи 3 фази або постійний струм. Показує найменший переріз для падіння до 3 %."),
]


def build_uk():
    import pages_electrical
    cards = {"battery-runtime": (pages_electrical.UK_CARDS["battery-runtime"], "battery", '<script src="{rel}assets/battery-uk.js"></script>',
                                 '<link rel="stylesheet" href="{rel}assets/battery-uk.css">\n'),
             "inverter-cable": (CABLE_UK_CARD, "cable-uk", '<script src="{rel}assets/embed-uk.js"></script>', ""),
             "voltage-drop": (VD_UK_CARD, "vd-uk", '<script src="{rel}assets/embed-uk.js"></script>', "")}
    blocks = []
    for name, title, path, height, lead in UK_EMBEDS:
        card, calc, js, head = cards[name]
        c.embed_page(name, title, path, "t-elec", calc, card, None, js, lang="uk", sub="uk/", head=head)
        code = snippet(name, title, path, height, sub="uk/", credit="Калькулятор:")
        full = "повна сторінка" if "/uk/" in path else "повна сторінка, англ."
        blocks.append(f'<div class="embed-item"><h3>{e(title)}</h3><p class="muted">{lead} <a href="{{rel}}{path}">{e(title)} ({full})</a></p>'
                      f'<textarea class="embed-code" readonly rows="6" aria-label="Код для вставки: {e(title)}">{e(code)}</textarea>'
                      f'<iframe src="{{rel}}embed/uk/{name}.html" title="{e(title)}: попередній перегляд" height="{height}" loading="lazy"></iframe></div>')
    faq_html, faq_ld = c.B.faq([
        ("Це безкоштовно? Потрібна реєстрація?", "Безкоштовно, без реєстрації і без ключа. Скопіюйте код і вставте на свою сторінку."),
        ("Що побачать відвідувачі?", "Лише калькулятор з невеликим рядком «Калькулятор: Dre Dev Tools», а під рамкою один рядок із посиланням на повну сторінку "
         "з формулами і джерелами. Усередині рамки немає реклами, cookie й аналітики."),
        ("Чи можна змінити розмір?", "Так. Ширина підлаштовується під сторінку до 720 px. Якщо калькулятор обрізано або під ним порожнє місце, змініть число height у коді."),
        ("Чи оновлюватимуться цифри?", "Так. Рамка завантажує калькулятор з цього сайту, тож виправлення з'являються на вашій сторінці без змін з вашого боку."),
        ("На яких платформах працює?", "Скрізь, де можна вставити HTML: WordPress (блок «Довільний HTML»), Хорошоп, Prom.ua (опис з HTML-кодом, якщо редактор "
         "дозволяє iframe), Wix (Embed HTML), Shopify, Tilda (блок T123) і звичайні HTML-сайти."),
    ])
    faq_html = faq_html.replace("<h2>Questions</h2>", "<h2>Питання</h2>")
    faq_ld["inLanguage"] = "uk"
    body = f"""
{c.CSS}
<div class="crumbs"><a href="{{rel}}index.html">Інструменти</a> › <a href="{{rel}}embed/">Вбудувати</a> › Українською</div>
<div class="hero"><div class="eyebrow">Для магазинів АКБ та інверторів, ОСББ і блогів</div><h1>Калькулятор резервного живлення на ваш сайт</h1>
<p class="lead">Покажіть відвідувачам, на скільки вистачить акумулятора, який кабель потрібен до інвертора і яке буде падіння напруги. Короткий код, безкоштовно, без реєстрації і без реклами в рамці.</p></div>
<section class="prose"><h2>Як додати</h2>
<ol><li>Виберіть калькулятор нижче і скопіюйте його код.</li>
<li>Вставте код на сторінку, де має бути калькулятор (блок HTML або коду у вашому конструкторі сайту).</li>
<li>Опублікуйте. Якщо калькулятор обрізано, збільште число <code>height</code>.</li></ol>
<p>Код має дві частини: сам калькулятор і рядок під ним «Калькулятор: Dre Dev Tools» з посиланням на повну сторінку з формулами і джерелами. Залиште обидві як є. Посилання має <code>rel="nofollow"</code>: воно не передає вашу «вагу» в пошуку і відповідає правилам пошуковиків щодо віджетів.</p></section>
<section class="prose"><h2>Умови простими словами</h2>
<ul><li>Безкоштовно для будь-якого сайту, зокрема інтернет-магазину чи сайту ОСББ. Без реєстрації, ключа і ліміту переглядів.</li>
<li>Залиште рядок «Калькулятор: Dre Dev Tools» з посиланням під рамкою. Це єдине, що просимо натомість.</li>
<li>Не змінюйте калькулятор, не ховайте підпис усередині рамки і не видавайте його за власний інструмент.</li>
<li>Це довідкові інструменти: обмеження з <a href="{{rel}}methodology.html">методики (англ.)</a> діють і на вашому сайті. Перед підключенням обладнання звіряйтеся з паспортами й інструкціями виробника.</li>
<li>Калькулятор можуть оновити, коли виправляють число; виправлення записуються в <a href="{{rel}}changelog.html">журнал змін (англ.)</a>.</li></ul></section>
<section><h2>Калькулятори для вставки</h2>{"".join(blocks)}</section>
{faq_html}
<p class="note">Питання або потрібен інший калькулятор українською: <a href="mailto:{c.B.CFG["support_email"]}">{c.B.CFG["support_email"]}</a>. <a href="{{rel}}embed/" hreflang="en">Embed page in English</a> (concrete, roofing, HVAC, soap and more).</p>
"""
    c.B.shell("embed/uk/index.html", "Безкоштовний калькулятор для вашого сайту: АКБ, кабель, падіння напруги (iframe) | Dre Dev Tools",
              "Вбудуйте на сайт магазину, ОСББ чи блогу калькулятор українською: на скільки вистачить АКБ або ДБЖ, переріз кабелю до інвертора, "
              "падіння напруги. Код iframe, безкоштовно, без реєстрації.",
              body, "", "embed", [faq_ld], c.scripts(), lang="uk", alternates=alternates())
