const fs = require('fs');
const path = require('path');

async function renderPdf(htmlFile, pdfFile) {
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const fileUrl = 'file://' + path.resolve(htmlFile).replace(/\\/g, '/');
  await page.goto(fileUrl, { waitUntil: 'networkidle' });
  await page.pdf({
    path: path.resolve(pdfFile),
    format: 'A4',
    printBackground: true,
    margin: { top: '15mm', right: '12mm', bottom: '15mm', left: '12mm' }
  });
  await browser.close();
}

module.exports = { renderPdf };
