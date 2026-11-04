// Exercise the visible navigation instead of a hidden phone-only select.
export async function chooseCollection(page,value){
 const select=page.getByLabel('Show collection',{exact:true});
 if(await select.isVisible())return select.selectOption(value);
 if(typeof value==='string'&&value)await page.waitForFunction(v=>Array.from(document.querySelector('#collection-type-filter')?.options||[]).some(option=>option.value===v),value);
 const name=typeof value==='object'&&value.label?value.label:value?await select.evaluate((el,v)=>Array.from(el.options).find(o=>o.value===v)?.textContent,value):'All items';
 if(!name)throw new Error('Collection choice not loaded: '+value);
 await page.getByRole('navigation',{name:'Collections',exact:true}).getByRole('button',{name,exact:true}).click();
}
export async function showIntake(page){
 const back=page.getByRole('button',{name:'Back to collection',exact:true});if(await back.isVisible())await back.click();
 const intake=page.locator('.item-intake');
 if(!(await intake.isVisible())){await page.getByRole('button',{name:'Add an item',exact:true}).click();await intake.getByRole('form',{name:'Add an item',exact:true}).waitFor();}
 await intake.waitFor();
}
export async function showTools(page){
 const summary=page.getByText('Collection tools and imports',{exact:true});
 if(await summary.count()&&!(await summary.evaluate(el=>el.parentElement.open)))await summary.click();
}
export async function editCopy(page){
 if(await page.locator('.item-intake').isVisible())await page.locator('.item-intake').getByRole('button',{name:/^Back to /}).click();
 if(!(await page.locator('.copy-inspector').isVisible()))await page.locator('.copy-row[aria-pressed="true"]').click();
 const form=page.getByRole('form',{name:'Edit copy details',exact:true});
 if(!(await form.isVisible()))await page.getByRole('button',{name:'Edit details',exact:true}).click();
}

export async function openDisclosure(page,name){
 const summary=page.getByText(name,{exact:true});await summary.waitFor();
 if(!(await summary.evaluate(el=>el.parentElement.open)))await summary.click();
}
