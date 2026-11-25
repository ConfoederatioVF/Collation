const puppeteer = require('puppeteer');
const fs = require('fs');

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

    await page.goto('https://www.jewishgen.org/Communities/Search.asp', { waitUntil: 'domcontentloaded', timeout: 25000 });
    await page.select('select[name="Country"]', 'Belarus');
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }),
      page.click('input[type="submit"], button[type="submit"]')
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const html = await page.content();
    fs.writeFileSync('tests/belarus_pale_cache/jg_belarus_search.html', html);
    const info = await page.evaluate(() => ({
      url: location.href,
      title: document.title,
      rows: document.querySelectorAll('table tr').length,
      text: document.body.innerText.slice(0, 1200)
    }));
    console.log('JG Belarus Search Result:', JSON.stringify(info, null, 2));
  } finally {
    if (browser) await browser.close();
  }
})();
