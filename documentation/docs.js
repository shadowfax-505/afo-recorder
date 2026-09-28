const menu=document.querySelector('.docs-menu');
const nav=document.querySelector('.docs-nav');
if(menu&&nav){
  menu.addEventListener('click',()=>{
    const open=nav.classList.toggle('open');
    menu.setAttribute('aria-expanded',String(open));
    menu.textContent=open?'Close contents':'Contents';
  });
  nav.addEventListener('click',event=>{
    if(event.target.closest('a')&&matchMedia('(max-width:760px)').matches){
      nav.classList.remove('open');
      menu.setAttribute('aria-expanded','false');
      menu.textContent='Contents';
    }
  });
}

const sectionLinks=[...document.querySelectorAll('.docs-nav a[href^="#"]')];
const sections=sectionLinks.map(link=>document.querySelector(link.hash)).filter(Boolean);
if('IntersectionObserver' in window){
  const observer=new IntersectionObserver(entries=>{
    const visible=entries.filter(entry=>entry.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
    if(!visible)return;
    sectionLinks.forEach(link=>link.classList.toggle('current',link.hash==='#'+visible.target.id));
  },{rootMargin:'-18% 0px -68% 0px',threshold:0});
  sections.forEach(section=>observer.observe(section));
}

document.querySelectorAll('pre.code').forEach(block=>{
  const button=document.createElement('button');
  button.className='copy-code';
  button.type='button';
  button.textContent='Copy';
  button.setAttribute('aria-label','Copy command');
  button.addEventListener('click',async()=>{
    const code=block.querySelector('code')?.textContent||'';
    await navigator.clipboard.writeText(code.trim());
    button.textContent='Copied';
    setTimeout(()=>button.textContent='Copy',1500);
  });
  block.append(button);
});
