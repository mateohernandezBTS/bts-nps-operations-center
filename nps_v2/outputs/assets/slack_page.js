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
  async function copyPayload(btn){
    var tpl=document.getElementById(btn.getAttribute('data-copy'));
    var holder=document.createElement('div');
    holder.appendChild(tpl.content.cloneNode(true));
    var table=holder.querySelector('table');
    embedQrImages(btn.closest('article'),table);
    var htmlText=table.outerHTML;
    try{
      if(navigator.clipboard&&window.ClipboardItem&&navigator.clipboard.write){
        await navigator.clipboard.write([new ClipboardItem({
          'text/html':new Blob([htmlText],{type:'text/html'}),
          'text/plain':new Blob([plainText(table)],{type:'text/plain'})})]);
      }else{
        holder.style.position='fixed';holder.style.left='-9999px';
        document.body.appendChild(holder);
        var sel=window.getSelection(),range=document.createRange();
        sel.removeAllRanges();range.selectNode(table);sel.addRange(range);
        var ok=document.execCommand('copy');sel.removeAllRanges();holder.remove();
        if(!ok){throw new Error('copy failed');}
      }
      flash(btn,true,'Copiado ✓');
    }catch(e){flash(btn,false,'No se pudo copiar');}
  }
  function copyQr(btn){
    var canvas=btn.parentElement.querySelector('canvas');
    if(!canvas||!navigator.clipboard||!window.ClipboardItem){
      flash(btn,false,'No disponible');return;}
    canvas.toBlob(function(blob){
      navigator.clipboard.write([new ClipboardItem({'image/png':blob})])
        .then(function(){flash(btn,true,'QR copiado ✓');})
        .catch(function(){flash(btn,false,'No se pudo');});
    },'image/png');
  }
  document.addEventListener('click',function(ev){
    var b=ev.target.closest('button');if(!b){return;}
    if(b.hasAttribute('data-copy')){copyPayload(b);}
    else if(b.hasAttribute('data-copy-qr')){copyQr(b);}
  });
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',renderQrs);
  }else{renderQrs();}
})();
