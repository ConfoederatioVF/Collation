const puppeteer = require('puppeteer');

(async () => {
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    // 1. JewishGen Communities Search form & country options
    await page.goto('https://www.jewishgen.org/Communities/Search.asp', { waitUntil: 'domcontentloaded', timeout: 25000 });
    const jgForm = await page.evaluate(() => {
      const selects = [...document.querySelectorAll('select')].map(s => ({
        name: s.name, id: s.id,
        options: [...s.options].slice(0, 30).map(o => ({ val: o.value, txt: o.text.trim() }))
      }));
      const inputs = [...document.querySelectorAll('input')].map(i => ({ name: i.name, type: i.type, value: i.value }));
      return { selects, inputs };
    });
    console.log('JG Search Form:', JSON.stringify(jgForm, null, 2).slice(0, 1500));

    // 2. Virtual Shtetl towns page
    await page.goto('https://sztetl.org.pl/en/towns', { waitUntil: 'domcontentloaded', timeout: 25000 });
    await new Promise(r => setTimeout(r, 2000));
    const vsSnippet = await page.evaluate(() => ({
      title: document.title,
      links: [...document.querySelectorAll('a')].map(a => ({ href: a.href, txt: a.innerText.trim() })).filter(x => x.txt).slice(0, 25)
    }));
    console.log('Virtual Shtetl:', JSON.stringify(vsSnippet, null, 2).slice(0, 1200));

    // 3. SGKP search form
    await page.goto('https://dir.icm.edu.pl/Slownik_geograficzny/', { waitUntil: 'domcontentloaded', timeout: 25000 });
    const sgkpInfo = await page.evaluate(() => ({
      forms: [...document.querySelectorAll('form')].map(f => ({ action: f.action, method: f.method, inputs: [...f.querySelectorAll('input,select')].map(i => i.name) })),
      links: [...document.querySelectorAll('a')].map(a => ({ href: a.href, txt: a.innerText.trim() })).slice(0, 20)
    }));
    console.log('SGKP:', JSON.stringify(sgkpInfo, null, 2).slice(0, 1000));
  } finally {
    if (browser) await browser.close();
  }
})();
