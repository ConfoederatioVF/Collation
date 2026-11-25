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

    await page.goto('https://sztetl.org.pl/en/towns', { waitUntil: 'domcontentloaded', timeout: 25000 });
    await new Promise(r => setTimeout(r, 2000));
    const info = await page.evaluate(() => {
      const selects = [...document.querySelectorAll('select')].map(s => ({
        name: s.name, id: s.id,
        opts: [...s.options].slice(0, 30).map(o => ({ val: o.value, txt: o.text.trim() }))
      }));
      const links = [...document.querySelectorAll('a')].map(a => ({ href: a.href, txt: a.innerText.trim() }))
        .filter(x => x.href.includes('/towns/') || x.href.includes('belarus'));
      return { selects, links: links.slice(0, 25), body: document.body.innerText.slice(0, 800) };
    });
    console.log('Virtual Shtetl /en/towns:', JSON.stringify(info, null, 2));
  } finally {
    if (browser) await browser.close();
  }
})();
