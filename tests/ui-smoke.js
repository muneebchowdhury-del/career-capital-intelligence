const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const base = process.argv[2] || 'http://127.0.0.1:4173/';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const pageErrors = [];
  page.on('pageerror', err => pageErrors.push(String(err)));

  await page.goto(base, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForSelector('#profile .profileRow', { timeout: 20000 });

  assert.ok((await page.locator('#tbody tr').count()) >= 16, 'opportunity table did not render');
  assert.ok((await page.locator('#profile .profileRow').count()) >= 7, 'personal-fit dimensions did not render');

  const firstRow = page.locator('#profile .profileRow').first();
  const toggle = firstRow.locator('input[type=checkbox]');
  const slider = firstRow.locator('input[type=range]');
  const importance = firstRow.locator('select');

  assert.equal(await toggle.isChecked(), false, 'profile toggle should start inactive');
  assert.equal(await slider.isDisabled(), true, 'profile slider should start disabled');
  assert.equal(await importance.isDisabled(), true, 'importance selector should start disabled');

  await toggle.click();
  assert.equal(await toggle.isChecked(), true, 'profile toggle did not activate');
  assert.equal(await slider.isDisabled(), false, 'profile slider did not enable');
  assert.equal(await importance.isDisabled(), false, 'importance selector did not enable');

  await slider.evaluate(el => {
    el.value = '80';
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
  assert.equal(await firstRow.locator('output').textContent(), '80', 'profile slider did not update');
  await importance.selectOption('3');

  await page.selectOption('#objective', 'fit');
  await page.selectOption('#geo', { label: 'Germany' });
  await page.selectOption('#horizon', '3-5y');
  const caption = await page.locator('#topCaption').textContent();
  assert.ok(caption.includes('Personal Strategic Fit'), 'objective change did not update ranking context');
  assert.ok(caption.includes('Germany'), 'geography change did not update ranking context');

  await page.locator('#topCards .rankCard').first().click();
  assert.ok(await page.locator('#drawer').evaluate(el => el.classList.contains('on')), 'detail drawer did not open');
  await page.click('#closeDrawer');
  assert.equal(await page.locator('#drawer').evaluate(el => el.classList.contains('on')), false, 'detail drawer did not close');

  assert.ok(await page.locator('#laborIntelligenceSection').count(), 'labor intelligence panel did not render');

  await page.click('#reset');
  assert.equal(await toggle.isChecked(), false, 'reset did not clear profile toggle');
  assert.equal(await slider.isDisabled(), true, 'reset did not disable profile slider');
  assert.equal(await slider.inputValue(), '50', 'reset did not restore neutral profile value');

  assert.deepEqual(pageErrors, [], `browser page errors: ${pageErrors.join(' | ')}`);
  await browser.close();
  console.log(`UI smoke test passed: ${base}`);
})().catch(err => {
  console.error(err);
  process.exit(1);
});
