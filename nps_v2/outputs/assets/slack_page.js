(function(){
  function renderQrs(){
    document.querySelectorAll('.qr').forEach(function(box){
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
  function flash(btn,ok,label){
    var original=btn.getAttribute('data-label')||btn.textContent;
    btn.setAttribute('data-label',original);
    btn.classList.add(ok?'ok':'fail');btn.textContent=label;
    setTimeout(function(){btn.classList.remove('ok','fail');btn.textContent=original;},1600);
  }
  function plainText(table){
    return Array.from(table.querySelectorAll('tr')).map(function(tr){
      return Array.from(tr.children).map(function(c){
        return c.innerText.trim();}).join('\t');}).join('\n');
  }
  function embedQrImages(card,table){
    // Payload rows follow the preview order: use the QR drawn in the browser, so the
    // copied image never depends on an external image service.
    var previewRows=card.querySelectorAll('table.preview tbody tr');
    Array.from(table.tBodies[0].rows).forEach(function(row,i){
      var canvas=previewRows[i]&&previewRows[i].querySelector('.qr canvas');
      var img=row.querySelector('img[alt="QR"]');
      if(canvas&&img){img.src=canvas.toDataURL('image/png');}
    });
  }
  // Copy strategy, most to least capable. Embedded viewers (for example a file preview
  // inside another app) often block the async Clipboard API, so every step falls back.
  async function writeAsync(items){
    if(!(navigator.clipboard&&window.ClipboardItem&&navigator.clipboard.write)){return false;}
    try{await navigator.clipboard.write([new ClipboardItem(items)]);return true;}
    catch(e){return false;}
  }
  function writeWithCopyEvent(data){
    var done=false;
    function onCopy(ev){
      Object.keys(data).forEach(function(type){ev.clipboardData.setData(type,data[type]);});
      ev.preventDefault();done=true;
    }
    document.addEventListener('copy',onCopy,true);
    try{document.execCommand('copy');}catch(e){}
    document.removeEventListener('copy',onCopy,true);
    return done;
  }
  function writeBySelection(node){
    var box=document.createElement('div');
    box.setAttribute('contenteditable','true');
    box.style.cssText='position:fixed;left:-10000px;top:0;opacity:0';
    box.appendChild(node);document.body.appendChild(box);
    var sel=window.getSelection(),range=document.createRange();
    range.selectNodeContents(box);sel.removeAllRanges();sel.addRange(range);
    var ok=false;try{ok=document.execCommand('copy');}catch(e){}
    sel.removeAllRanges();box.remove();return ok;
  }
  function manualCopy(node,message){
    // Last resort: show the content selected so Ctrl+C / Cmd+C copies it.
    var overlay=document.getElementById('manual-copy');
    overlay.querySelector('.mc-msg').textContent=message;
    var area=overlay.querySelector('.mc-area');area.innerHTML='';area.appendChild(node);
    overlay.hidden=false;
    var sel=window.getSelection(),range=document.createRange();
    range.selectNodeContents(area);sel.removeAllRanges();sel.addRange(range);
  }
  async function copyPayload(btn){
    var tpl=document.getElementById(btn.getAttribute('data-copy'));
    var holder=document.createElement('div');
    holder.appendChild(tpl.content.cloneNode(true));
    var table=holder.querySelector('table');
    embedQrImages(btn.closest('article'),table);
    var htmlText=table.outerHTML,text=plainText(table);
    if(await writeAsync({'text/html':new Blob([htmlText],{type:'text/html'}),
        'text/plain':new Blob([text],{type:'text/plain'})})
      ||writeWithCopyEvent({'text/html':htmlText,'text/plain':text})
      ||writeBySelection(table.cloneNode(true))){
      flash(btn,true,'Copiado ✓');return;
    }
    flash(btn,false,'Copiá a mano');
    manualCopy(table,'Este visor bloquea el portapapeles. La tabla ya está seleccionada: '
      +'presioná Ctrl+C (Cmd+C en Mac) y pegala en el canvas.');
  }
  async function copyQr(btn){
    var canvas=btn.parentElement.querySelector('canvas');
    if(!canvas){flash(btn,false,'No disponible');return;}
    var dataUrl=canvas.toDataURL('image/png');
    var blob=await new Promise(function(resolve){canvas.toBlob(resolve,'image/png');});
    var img='<img src="'+dataUrl+'" alt="QR" width="150" height="150">';
    if((blob&&await writeAsync({'image/png':blob}))
      ||writeWithCopyEvent({'text/html':img})){
      flash(btn,true,'QR copiado ✓');return;
    }
    var node=document.createElement('img');node.src=dataUrl;node.alt='QR';
    node.width=150;node.height=150;
    flash(btn,false,'Copiá a mano');
    manualCopy(node,'Este visor bloquea el portapapeles. El QR ya está seleccionado: '
      +'presioná Ctrl+C (Cmd+C en Mac).');
  }
  document.addEventListener('click',function(ev){
    var b=ev.target.closest('button');if(!b){return;}
    if(b.hasAttribute('data-close-manual')){
      document.getElementById('manual-copy').hidden=true;return;}
    if(b.hasAttribute('data-copy')){copyPayload(b);}
    else if(b.hasAttribute('data-copy-qr')){copyQr(b);}
  });
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',renderQrs);
  }else{renderQrs();}
})();
