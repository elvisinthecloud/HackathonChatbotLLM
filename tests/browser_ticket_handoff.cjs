const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1280,height:1000}});
 const errors=[], requests=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/chat',async route=>{
  requests.push(route.request().postDataJSON());
  await route.fulfill({json:{answer:'Approved article guidance [1]',sources:[],context:{}}});
 });
 await page.goto('http://127.0.0.1:8765');
 await page.locator('#chatFab').click();
 await page.locator('#profileSelect').selectOption('student');
 await page.waitForFunction(()=>!document.getElementById('chatSend').disabled);
 for(const name of ['Account/Profile Issue','Courseware Issue','Roles and Permissions','Other']) {
  await page.getByRole('button',{name,exact:true}).waitFor({state:'visible'});
 }
 assert.equal(requests.length,0);
 await page.getByRole('button',{name:'Account/Profile Issue',exact:true}).click();
 assert.equal(requests.length,0);
 assert.match(await page.locator('#chatBody').innerText(),/Please tell me more about what’s happening and what you’re trying to do/);
 await page.locator('#chatInput').fill('Actually my Moodle course is missing.');
 await page.locator('#chatSend').click();
 await page.waitForFunction(()=>!document.getElementById('chatSend').disabled);
 assert.equal(requests.length,1);
 assert.equal(requests[0].message,'Actually my Moodle course is missing.');
 assert.equal(requests[0].issue_category,'Account/Profile Issue');
 assert.equal(requests[0].course_id,null);
 assert.equal(requests[0].system_area,null);
 assert.match(await page.locator('#chatBody').innerText(),/Approved article guidance/);
 await page.getByRole('button',{name:'Contact Help Desk',exact:true}).click();
 await page.locator('#supportPanel').waitFor({state:'visible'});
 assert.equal(await page.locator('#ticketPage').count(),0);
 await page.locator('#supportPanelClose').click();
 await page.locator('#btnClear').click();
 await page.waitForFunction(()=>!document.getElementById('chatSend').disabled);
 await page.getByRole('button',{name:'Other',exact:true}).waitFor({state:'visible'});
 assert.doesNotMatch(await page.locator('#chatBody').innerText(),/Actually my Moodle/);
 await page.getByRole('button',{name:'Other',exact:true}).click();
 await page.locator('#profileSelect').selectOption('instructor');
 await page.waitForFunction(()=>!document.getElementById('chatSend').disabled);
 await page.getByRole('button',{name:'Courseware Issue',exact:true}).waitFor({state:'visible'});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'/private/tmp/mcele-neutral-intake.png',fullPage:true});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('Passed: greeting/categories, neutral prompt, no early search, mistaken category, optional course/site, article response, Help Desk, reset/profile isolation, mobile.');
})().catch(e=>{console.error(e);process.exit(1)});
