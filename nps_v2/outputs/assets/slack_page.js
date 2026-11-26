(function(){
  var ui=window.BTSUI;
  function renderQrs(){
    document.querySelectorAll('.qr[data-text]').forEach(function(box){
      var text=box.getAttribute('data-text');
      try{
        new QRCode(box,{text:text,width:150,height:150,colorDark:'#24282B',
          colorLight:'#ffffff',correctLevel:QRCode.CorrectLevel.M});
      }catch(e){
        var src=box.getAttribute('data-fallback');
        if(src){var img=document.createElement('img');img.alt='QR';img.src=src;
          box.appendChild(img);}
      }
    });
  }
  function plainText(holder){
    return Array.from(holder.querySelectorAll('h3,p,hr')).map(function(el){
      if(el.tagName==='HR'){return '';}
      return el.querySelector('img')?'[QR]':el.textContent.trim();}).join('\n');
  }
  function embedQrImages(card,holder){
    // Swap each QR placeholder for the PNG drawn in the browser (same session order as
    // the card's list), so the copied image never depends on an external service.
    var items=card.querySelectorAll('ion-item.session');
    holder.querySelectorAll('img[data-row]').forEach(function(img){
      var item=items[Number(img.getAttribute('data-row'))];
      var canvas=item&&item.querySelector('.qr canvas');
      if(canvas){img.src=canvas.toDataURL('image/png');}
      img.removeAttribute('data-row');
    });
  }
  function payloadFor(card){
    var holder=document.createElement('div');
    holder.appendChild(card.querySelector('template').content.cloneNode(true));
    embedQrImages(card,holder);
    return holder;
  }
  async function copyPayload(btn){
    var holder=payloadFor(btn.closest('ion-card'));
    var htmlText=holder.innerHTML,text=plainText(holder);
    if(await ui.copyRich(
        {'text/html':new Blob([htmlText],{type:'text/html'}),
         'text/plain':new Blob([text],{type:'text/plain'})},
        {'text/html':htmlText,'text/plain':text},holder.cloneNode(true))){
      ui.notify(btn,true,'Copied for Slack ✓');return;
    }
    ui.notify(btn,false,'Copy by hand');
    ui.manualCopy(holder,'This viewer blocks the clipboard. The content is already '
      +'selected: press Ctrl+C (Cmd+C on Mac) and paste it into the canvas.');
  }
  async function copyQr(control){
    var canvas=control.closest('ion-item').querySelector('.qr canvas');
    if(!canvas){ui.notify(control,false,'Not available');return;}
    var dataUrl=canvas.toDataURL('image/png');
    var blob=await new Promise(function(resolve){canvas.toBlob(resolve,'image/png');});
    var img='<img src="'+dataUrl+'" alt="QR" width="150" height="150">';
    if(await ui.copyRich(blob?{'image/png':blob}:null,{'text/html':img},null)){
      ui.notify(control,true,'QR copied ✓');return;
    }
    var node=document.createElement('img');node.src=dataUrl;node.alt='QR';
    node.width=150;node.height=150;
    ui.notify(control,false,'Copy by hand');
    ui.manualCopy(node,'This viewer blocks the clipboard. The QR is already selected: '
      +'press Ctrl+C (Cmd+C on Mac).');
  }
  function fillSlackView(card){
    var box=card&&card.querySelector('.slack-cards');
    if(box&&!box.hasChildNodes()){box.appendChild(payloadFor(card));}
  }
  // Search and country tabs (available when Ionic is loaded).
  var query='',country='all';
  function applyFilters(){
    var any=false;
    document.querySelectorAll('section.country').forEach(function(section){
      var countryOk=country==='all'||section.getAttribute('data-country')===country;
      var sectionAny=false;
      section.querySelectorAll('ion-card.client').forEach(function(card){
        var cardAny=false;
        card.querySelectorAll('ion-item.session').forEach(function(item){
          var ok=countryOk&&(!query||item.getAttribute('data-search').indexOf(query)>=0);
          item.hidden=!ok;cardAny=cardAny||ok;
        });
        card.hidden=!cardAny;sectionAny=sectionAny||cardAny;
      });
      section.hidden=!sectionAny;any=any||sectionAny;
    });
    var none=document.getElementById('no-results');if(none){none.hidden=any;}
  }
  document.addEventListener('ionInput',function(ev){
    if(ev.target.tagName==='ION-SEARCHBAR'){
      query=(ev.detail.value||'').trim().toLowerCase();applyFilters();}
  });
  document.addEventListener('ionChange',function(ev){
    if(ev.target.tagName==='ION-SEGMENT'){country=ev.detail.value||'all';applyFilters();}
    else if(ev.target.classList&&ev.target.classList.contains('slack-view')&&ev.detail.value){
      fillSlackView(ev.target.closest('ion-card'));}
  });
  document.addEventListener('bts-open',function(ev){
    if(ev.target.closest('.slack-view')){fillSlackView(ev.target.closest('ion-card'));}
  });
  document.addEventListener('click',function(ev){
    var qr=ev.target.closest('.qr[data-text]');if(qr){copyQr(qr);return;}
    var b=ev.target.closest('ion-button');if(!b){return;}
    if(b.hasAttribute('data-copy')){copyPayload(b);}
    else if(b.hasAttribute('data-copy-qr')){copyQr(b);}
  });
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',renderQrs);
  }else{renderQrs();}
})();
