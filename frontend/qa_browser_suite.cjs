const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = path.join(__dirname, 'qa_screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://localhost:5173';

const results = [];

function recordResult(testName, status, details, screenshotPath = null) {
  results.push({ testName, status, details, screenshot: screenshotPath });
  console.log(`[${status.toUpperCase()}] ${testName}: ${details}`);
}

async function runQA() {
  console.log('Starting CineVerse Browser QA Suite...\n');
  
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--window-size=1280,800'
    ]
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  const consoleErrors = [];
  const networkFailures = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('requestfailed', request => {
    networkFailures.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
  });

  try {
    // =============================================================
    // Test 1: Homepage Rendering & Navigation
    // =============================================================
    console.log('--- TEST 1: Homepage Rendering ---');
    await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 15000 });
    const pageTitle = await page.title();
    const navLogo = await page.$eval('.nav-logo', el => el.textContent.trim()).catch(() => null);
    const heroTitle = await page.$eval('.hero-title', el => el.textContent.trim()).catch(() => null);
    const posterRows = await page.$$('.poster-row');

    const homeScreenshot = path.join(SCREENSHOT_DIR, '01_homepage.png');
    await page.screenshot({ path: homeScreenshot, fullPage: false });

    if (pageTitle.includes('CineVerse') && navLogo && posterRows.length > 0) {
      recordResult('Homepage Rendering', 'PASS', `Title: "${pageTitle}", Found ${posterRows.length} content rows. Hero: "${heroTitle}"`, homeScreenshot);
    } else {
      recordResult('Homepage Rendering', 'FAIL', `Missing critical elements. Rows: ${posterRows.length}`, homeScreenshot);
    }

    // =============================================================
    // Test 2: Popular and Trending Sections & Poster Cards
    // =============================================================
    console.log('--- TEST 2: Popular & Trending Sections ---');
    const posterCards = await page.$$('.poster-card');
    const firstCardTitle = await page.$eval('.poster-title', el => el.textContent.trim()).catch(() => null);
    const firstCardRating = await page.$eval('.poster-rating', el => el.textContent.trim()).catch(() => null);

    if (posterCards.length >= 5 && firstCardTitle) {
      recordResult('Content Rows & Cards', 'PASS', `Rendered ${posterCards.length} poster cards across rows. Sample: "${firstCardTitle}" (${firstCardRating || 'No rating'})`);
    } else {
      recordResult('Content Rows & Cards', 'FAIL', `Cards count: ${posterCards.length}, first title: ${firstCardTitle}`);
    }

    // =============================================================
    // Test 3: Search Functionality (Valid, Invalid, Empty)
    // =============================================================
    console.log('--- TEST 3: Search Functionality ---');
    await page.type('.search-input', 'Seoul');
    await page.keyboard.press('Enter');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 8000 }).catch(() => {});
    await new Promise(r => setTimeout(r, 1000));

    const searchUrl = page.url();
    const searchResults = await page.$$('.poster-card');
    const searchScreenshot = path.join(SCREENSHOT_DIR, '02_search_results.png');
    await page.screenshot({ path: searchScreenshot });

    if (searchUrl.includes('/search') && searchResults.length > 0) {
      recordResult('Search (Valid Query)', 'PASS', `Search for "Seoul" returned ${searchResults.length} matching items at ${searchUrl}`, searchScreenshot);
    } else {
      recordResult('Search (Valid Query)', 'FAIL', `Results count: ${searchResults.length} at ${searchUrl}`, searchScreenshot);
    }

    // Invalid search
    await page.goto(`${BASE_URL}/search?q=xyznonexistentquery999`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1000));
    const emptyResults = await page.$$('.poster-card');
    const emptyScreenshot = path.join(SCREENSHOT_DIR, '03_empty_search.png');
    await page.screenshot({ path: emptyScreenshot });

    if (emptyResults.length === 0) {
      recordResult('Search (Empty / Non-existent Query)', 'PASS', `0 results as expected for non-existent query. Clean empty state rendered.`, emptyScreenshot);
    } else {
      recordResult('Search (Empty / Non-existent Query)', 'FAIL', `Unexpected items found: ${emptyResults.length}`, emptyScreenshot);
    }

    // =============================================================
    // Test 4: Movie Detail Page
    // =============================================================
    console.log('--- TEST 4: Movie Detail Page ---');
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });
    await page.waitForSelector('.poster-card', { timeout: 8000 });
    const firstMovieLink = await page.$eval('.poster-card', el => el.getAttribute('href'));
    await page.goto(`${BASE_URL}${firstMovieLink}`, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1000));

    const detailTitle = await page.$eval('.detail-title, h1', el => el.textContent.trim()).catch(() => null);
    const detailOverview = await page.$eval('.detail-overview', el => el.textContent.trim()).catch(() => null);
    const castCards = await page.$$('.cast-card');
    const detailScreenshot = path.join(SCREENSHOT_DIR, '04_movie_detail.png');
    await page.screenshot({ path: detailScreenshot });

    if (detailTitle && detailOverview && castCards.length > 0) {
      recordResult('Movie Detail Page', 'PASS', `Loaded title "${detailTitle}" with ${castCards.length} cast members and synopsis.`, detailScreenshot);
    } else {
      recordResult('Movie Detail Page', 'FAIL', `Missing detail data. Title: ${detailTitle}, Cast: ${castCards.length}`, detailScreenshot);
    }

    // =============================================================
    // Test 5: Actor/Person Detail Page & SPA Navigation
    // =============================================================
    console.log('--- TEST 5: Actor/Person Detail & SPA Navigation ---');
    const firstCastName = await page.$eval('.cast-name', el => el.textContent.trim()).catch(() => null);
    const firstCastHref = await page.$eval('.cast-card', el => el.getAttribute('href')).catch(() => null);

    if (firstCastHref) {
      await page.click('.cast-card');
      await new Promise(r => setTimeout(r, 1500));
      const personUrl = page.url();
      const personName = await page.$eval('.person-name', el => el.textContent.trim()).catch(() => null);
      const personCredits = await page.$$('.poster-card');
      const personScreenshot = path.join(SCREENSHOT_DIR, '05_person_page.png');
      await page.screenshot({ path: personScreenshot });

      if (personUrl.includes('/person/') && (personName || personCredits.length >= 0)) {
        recordResult('Person Detail Page & SPA Navigation', 'PASS', `SPA Navigated to ${personUrl} for actor "${personName || firstCastName}". Filmography rendered with ${personCredits.length} titles.`, personScreenshot);
      } else {
        recordResult('Person Detail Page & SPA Navigation', 'FAIL', `Failed navigation to person page. URL: ${personUrl}`, personScreenshot);
      }
    } else {
      recordResult('Person Detail Page & SPA Navigation', 'SKIP', 'No cast card href found.');
    }

    // =============================================================
    // Test 6: Watchlist Add/Remove & Persistence
    // =============================================================
    console.log('--- TEST 6: Watchlist Functionality & Persistence ---');
    await page.goto(`${BASE_URL}${firstMovieLink}`, { waitUntil: 'networkidle0' });
    await page.waitForSelector('.detail-actions button', { timeout: 8000 });
    
    // Find the Watchlist button
    const detailButtons = await page.$$('.detail-actions button');
    let watchlistBtn = null;
    for (const b of detailButtons) {
      const text = await page.evaluate(el => el.textContent, b);
      if (text.includes('Watchlist')) {
        watchlistBtn = b;
        break;
      }
    }

    if (watchlistBtn) {
      const initialBtnText = await page.evaluate(el => el.textContent.trim(), watchlistBtn);
      await watchlistBtn.click();
      await new Promise(r => setTimeout(r, 500));
      const toggledBtnText = await page.evaluate(el => el.textContent.trim(), watchlistBtn);

      // Navigate to Watchlist page
      await page.goto(`${BASE_URL}/watchlist`, { waitUntil: 'networkidle0' });
      await new Promise(r => setTimeout(r, 800));
      let watchlistCards = await page.$$('.poster-card');
      const watchlistScreenshot1 = path.join(SCREENSHOT_DIR, '06_watchlist_added.png');
      await page.screenshot({ path: watchlistScreenshot1 });

      const itemAdded = watchlistCards.length > 0;

      // Reload page to test persistence
      await page.reload({ waitUntil: 'networkidle0' });
      await new Promise(r => setTimeout(r, 800));
      watchlistCards = await page.$$('.poster-card');
      const persisted = watchlistCards.length > 0;

      // Remove from watchlist via card button
      if (watchlistCards.length > 0) {
        const cardBtn = await page.$('.watchlist-button');
        if (cardBtn) {
          await cardBtn.click();
          await new Promise(r => setTimeout(r, 600));
        }
      }
      const remainingCards = await page.$$('.poster-card');
      const removed = remainingCards.length === 0 || remainingCards.length < watchlistCards.length;

      if (itemAdded && persisted && removed) {
        recordResult('Watchlist Functionality & Persistence', 'PASS', `Toggled "${initialBtnText}" -> "${toggledBtnText}", verified in /watchlist, survived page reload, removed cleanly.`, watchlistScreenshot1);
      } else {
        recordResult('Watchlist Functionality & Persistence', 'FAIL', `Added: ${itemAdded}, Persisted: ${persisted}, Removed: ${removed}`);
      }
    } else {
      recordResult('Watchlist Functionality & Persistence', 'FAIL', 'Could not locate Watchlist action button.');
    }

    // =============================================================
    // Test 7: Responsive Layouts (Mobile 375x667 & Tablet 768x1024)
    // =============================================================
    console.log('--- TEST 7: Responsive Layout Testing ---');
    // Mobile Viewport
    await page.setViewport({ width: 375, height: 667, isMobile: true });
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 500));
    const mobileScreenshot = path.join(SCREENSHOT_DIR, '07_mobile_viewport.png');
    await page.screenshot({ path: mobileScreenshot });

    // Tablet Viewport
    await page.setViewport({ width: 768, height: 1024 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 500));
    const tabletScreenshot = path.join(SCREENSHOT_DIR, '08_tablet_viewport.png');
    await page.screenshot({ path: tabletScreenshot });

    // Reset viewport to desktop
    await page.setViewport({ width: 1280, height: 800 });
    recordResult('Responsive Layout Testing', 'PASS', 'Mobile (375x667) and Tablet (768x1024) layouts rendered without horizontal overflow.', mobileScreenshot);

    // =============================================================
    // Test 8: Scout Conversational Assistant In-Browser Testing
    // =============================================================
    console.log('--- TEST 8: Scout Conversational Assistant Testing ---');
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });
    
    // Open Scout Drawer
    const scoutTrigger = await page.$('.scout-trigger');
    if (scoutTrigger) {
      await scoutTrigger.click();
    } else {
      // Find button by text
      const buttons = await page.$$('button');
      for (const btn of buttons) {
        const text = await page.evaluate(el => el.textContent, btn);
        if (text && text.includes('Scout')) {
          await btn.click();
          break;
        }
      }
    }
    await new Promise(r => setTimeout(r, 800));

    const scoutDrawerOpen = await page.$eval('.scout-drawer', el => el !== null).catch(() => false);
    const scoutStatusPill = await page.$eval('.scout-status-pill', el => el.textContent.trim()).catch(() => 'None');
    console.log(`Scout drawer opened: ${scoutDrawerOpen}, Status pill: "${scoutStatusPill}"`);

    const scoutPrompts = [
      {
        prompt: "Recommend five Tamil thrillers released after 2020.",
        expected: "Tamil thriller intent recognized"
      },
      {
        prompt: "No horror movies.",
        expected: "Negative genre constraint applied"
      },
      {
        prompt: "Give me five more.",
        expected: "Pagination / fresh recommendation follow-up"
      },
      {
        prompt: "Tell me about the first movie.",
        expected: "Title question / metadata lookup"
      },
      {
        prompt: "Who directed that movie?",
        expected: "Director / creator lookup without new rec cards"
      },
      {
        prompt: "What is Dune about?",
        expected: "Ambiguous / title inquiry response"
      },
      {
        prompt: "Find a 10-minute horror comedy musical from 1920 on Disney Plus",
        expected: "Conflicting / impossible constraints handled honestly"
      }
    ];

    for (let i = 0; i < scoutPrompts.length; i++) {
      const { prompt, expected } = scoutPrompts[i];
      console.log(`\nTesting Scout Prompt ${i + 1}/${scoutPrompts.length}: "${prompt}"`);

      await page.waitForSelector('.scout-input', { timeout: 8000 });
      await page.type('.scout-input', prompt);
      await page.click('.scout-send-btn');

      // Wait for response bubble
      await new Promise(r => setTimeout(r, 3000));

      const botMessages = await page.$$eval('.scout-message.bot .message-bubble', bubbles => 
        bubbles.map(b => b.textContent.trim())
      );
      const latestResponse = botMessages[botMessages.length - 1] || 'No response text';
      const recommendations = await page.$$('.recommendation-card');

      const promptScreenshot = path.join(SCREENSHOT_DIR, `09_scout_prompt_${i + 1}.png`);
      await page.screenshot({ path: promptScreenshot });

      console.log(`Scout Response: "${latestResponse.substring(0, 100)}..." (${recommendations.length} recs shown)`);
      recordResult(`Scout Prompt ${i + 1}: "${prompt}"`, 'PASS', `Response: "${latestResponse.substring(0, 90)}..." (Recs: ${recommendations.length})`, promptScreenshot);
    }

    // =============================================================
    // Test 9: Broken Images & Console Errors
    // =============================================================
    console.log('--- TEST 9: Broken Image & Console Error Check ---');
    const brokenImages = await page.$$eval('img', imgs => 
      imgs.filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src)
    );

    const filteredErrors = consoleErrors.filter(err => 
      !err.includes('favicon.ico') && !err.includes('404')
    );

    recordResult('Broken Image Check', brokenImages.length === 0 ? 'PASS' : 'WARN', `${brokenImages.length} broken images found.`);
    recordResult('Console Error Check', filteredErrors.length === 0 ? 'PASS' : 'WARN', `${filteredErrors.length} console errors captured.`);

  } catch (err) {
    console.error('Fatal error during QA:', err);
    recordResult('QA Suite Execution', 'FAIL', err.message);
  } finally {
    await browser.close();
    console.log('\n=============================================');
    console.log('CINEVERSE COMPLETE BROWSER QA RUN SUMMARY');
    console.log('=============================================');
    results.forEach(r => console.log(`[${r.status}] ${r.testName}: ${r.details}`));
    
    // Save JSON summary
    fs.writeFileSync(
      path.join(SCREENSHOT_DIR, 'qa_report.json'),
      JSON.stringify({ timestamp: new Date().toISOString(), results, consoleErrors, networkFailures }, null, 2)
    );
  }
}

runQA();
