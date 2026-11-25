const puppeteer = require('puppeteer');

(async () => {
  let browser;
  try {
    browser = await puppeteer.launch({
      headless: true,
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      args: ['--no-sandbox']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    console.log('=== 1. data.gov.lt/datasets/2938/ ===');
    await page.goto('https://data.gov.lt/datasets/2938/', { waitUntil: 'networkidle2', timeout: 30000 }).catch(e => console.log('goto err:', e.message));
    const info2938 = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a')).map(a => ({ text: a.innerText.trim(), href: a.href }));
      return { title: document.title, text: document.body.innerText.slice(0, 1500), links: links.filter(l => /get\.data\.gov|download|json|csv|api|gyvent/i.test(l.href + ' ' + l.text)).slice(0, 20) };
    });
    console.log(JSON.stringify(info2938, null, 2));

    console.log('=== 2. data.gov.lt search gyventojai gyvenvietese ===');
    await page.goto('https://data.gov.lt/datasets?q=gyvenviet%C4%97se', { waitUntil: 'networkidle2', timeout: 30000 }).catch(e => console.log('goto2 err:', e.message));
    const searchRes = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a')).map(a => ({ text: a.innerText.trim(), href: a.href })).filter(l => l.href.includes('/datasets/')).slice(0, 25);
    });
    console.log(JSON.stringify(searchRes, null, 2));

    console.log('=== 3. osp.stat.gov.lt ===');
    await page.goto('https://osp.stat.gov.lt/gyventoju-ir-bustu-surasymai1', { waitUntil: 'networkidle2', timeout: 30000 }).catch(e => console.log('goto3 err:', e.message));
    const ospRes = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a')).map(a => ({ text: a.innerText.trim(), href: a.href }));
      return { title: document.title, links: links.filter(l => /xlsx|csv|xls|zip|json|sura|gyvenv|rodikl/i.test(l.href + ' ' + l.text)).slice(0, 30) };
    });
    console.log(JSON.stringify(ospRes, null, 2));
  } finally {
    if (browser) await browser.close();
  }
})();
