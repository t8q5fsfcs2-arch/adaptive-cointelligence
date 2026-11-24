// D007: light or dark mode. A local browser preference only; follows the system until chosen.
(function(){
 var saved=null;try{saved=localStorage.getItem('ac-theme');}catch(e){}
 var dark=saved?saved==='dark':!!(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);
 document.documentElement.setAttribute('data-theme',dark?'dark':'light');
})();
function acTheme(){return document.documentElement.getAttribute('data-theme')==='dark'?'dark':'light';}
function acToggleTheme(){
 var next=acTheme()==='dark'?'light':'dark';
 document.documentElement.setAttribute('data-theme',next);
 try{localStorage.setItem('ac-theme',next);}catch(e){}
 var b=document.querySelector('.theme-toggle');if(b)b.setAttribute('aria-label','Switch to '+(next==='dark'?'light':'dark')+' mode');
}
function acThemeToggleButton(){
 var dark=acTheme()==='dark';
 var sun='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5"/></svg>';
 var moon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/></svg>';
 return '<button type="button" class="theme-toggle" data-action="theme-toggle" aria-label="Switch to '+(dark?'light':'dark')+' mode"><span class="when-light">'+moon+'<span class="tt-text">Dark</span></span><span class="when-dark">'+sun+'<span class="tt-text">Light</span></span></button>';
}
