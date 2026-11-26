(function(){
  // Shared behaviour of V2 views (see nps_v2/outputs/ui_kit.py).
  var ui={ready:false};
  if(window.customElements){
    customElements.whenDefined('ion-card').then(function(){ui.ready=true;});
  }
  ui.notify=function(control,ok,label){
    var toast=document.getElementById('bts-toast');
    if(ui.ready&&toast&&toast.present){
      toast.message=label;toast.color=ok?'dark':'danger';toast.present();return;}
    if(!control||control.hasAttribute('data-no-label')){return;}
    var original=control.getAttribute('data-label')||control.textContent;
    control.setAttribute('data-label',original);control.textContent=label;
    setTimeout(function(){control.textContent=original;},1600);
  };
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
  // Copy strategy, most to least capable. Embedded viewers often block the async
  // Clipboard API, so every step falls back. Returns true when something was copied.
  ui.copyRich=async function(blobs,data,node){
    return (blobs&&await writeAsync(blobs))
      ||(data&&writeWithCopyEvent(data))
      ||(node?writeBySelection(node):false);
  };
  ui.manualCopy=function(node,message){
    // Last resort: show the content selected so Ctrl+C / Cmd+C copies it.
    var overlay=document.getElementById('manual-copy');
    overlay.querySelector('.mc-msg').textContent=message;
    var area=overlay.querySelector('.mc-area');area.innerHTML='';area.appendChild(node);
    overlay.hidden=false;
    var sel=window.getSelection(),range=document.createRange();
    range.selectNodeContents(area);sel.removeAllRanges();sel.addRange(range);
  };
  document.addEventListener('click',function(ev){
    if(ev.target.closest('[data-close-manual]')){
      document.getElementById('manual-copy').hidden=true;return;}
    var header=ev.target.closest('ion-accordion [slot=header]');
    if(header&&!ui.ready){
      var acc=header.closest('ion-accordion');acc.classList.toggle('open');
      acc.dispatchEvent(new CustomEvent('bts-open',{bubbles:true}));
    }
  });
  window.BTSUI=ui;
})();
