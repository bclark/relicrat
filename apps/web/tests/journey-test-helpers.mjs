// Choose from the desktop rail or the phone's collection home.
export async function chooseCollection(page,value){
 const nav=page.getByRole('navigation',{name:'Collections',exact:true});
 if(!(await nav.isVisible())){
  const intake=page.locator('.item-intake');
  const detailBack=page.locator('.back-to-collection');
  if(await intake.isVisible())await intake.getByRole('button',{name:/^Back to /}).click();
  if(await detailBack.isVisible())await detailBack.click();
  if(!(await nav.isVisible()))await page.locator('.phone-back').click();
 }
 const choice=typeof value==='object'?nav.getByRole('button',{name:value.label,exact:true}):nav.locator('[data-collection='+JSON.stringify(value)+']');
 await choice.click();
}
export async function showIntake(page){
 const back=page.locator('.back-to-collection');if(await back.isVisible())await back.click();
 const intake=page.locator('.item-intake');
 if(!(await intake.isVisible())){await page.getByRole('button',{name:'Add an item',exact:true}).click();await intake.getByRole('form',{name:'Add an item',exact:true}).waitFor();}
 await intake.waitFor();
}
export async function showTools(page){
 const summary=page.locator('.collection-tools > summary');
 if(!await summary.isVisible()&&await page.getByRole('button',{name:'Menu',exact:true}).isVisible()){
  await page.getByRole('button',{name:'Menu',exact:true}).click();
  await page.getByRole('button',{name:'Collection tools and imports',exact:true}).click();
 }
 if(await summary.count()&&!(await summary.evaluate(el=>el.parentElement.open)))await summary.click();
}
export async function editCopy(page){
 if(await page.locator('.item-intake').isVisible())await page.locator('.item-intake').getByRole('button',{name:/^Back to /}).click();
 if(!(await page.locator('.copy-inspector').isVisible()))await page.locator('.copy-row[aria-pressed="true"]').click();
 const form=page.getByRole('form',{name:'Edit copy details',exact:true});
 if(!(await form.isVisible()))await page.getByRole('button',{name:/^(Edit details|Continue editing)$/,exact:true}).click();
}

export async function openDisclosure(page,name){
 const summary=page.getByText(name,{exact:true});await summary.waitFor();
 if(!(await summary.evaluate(el=>el.parentElement.open)))await summary.click();
}
