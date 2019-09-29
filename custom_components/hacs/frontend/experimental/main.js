function t(t,e,i,s){var o,r=arguments.length,n=r<3?e:null===s?s=Object.getOwnPropertyDescriptor(e,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,i,s);else for(var a=t.length-1;a>=0;a--)(o=t[a])&&(n=(r<3?o(n):r>3?o(e,i,n):o(e,i))||n);return r>3&&n&&Object.defineProperty(e,i,n),n}const e=new WeakMap,i=t=>"function"==typeof t&&e.has(t),s=void 0!==window.customElements&&void 0!==window.customElements.polyfillWrapFlushCallback,o=(t,e,i=null)=>{for(;e!==i;){const i=e.nextSibling;t.removeChild(e),e=i}},r={},n={},a=`{{lit-${String(Math.random()).slice(2)}}}`,p=`\x3c!--${a}--\x3e`,h=new RegExp(`${a}|${p}`),c="$lit$";class l{constructor(t,e){this.parts=[],this.element=e;const i=[],s=[],o=document.createTreeWalker(e.content,133,null,!1);let r=0,n=-1,p=0;const{strings:l,values:{length:u}}=t;for(;p<u;){const t=o.nextNode();if(null!==t){if(n++,1===t.nodeType){if(t.hasAttributes()){const e=t.attributes,{length:i}=e;let s=0;for(let t=0;t<i;t++)d(e[t].name,c)&&s++;for(;s-- >0;){const e=l[p],i=f.exec(e)[2],s=i.toLowerCase()+c,o=t.getAttribute(s);t.removeAttribute(s);const r=o.split(h);this.parts.push({type:"attribute",index:n,name:i,strings:r}),p+=r.length-1}}"TEMPLATE"===t.tagName&&(s.push(t),o.currentNode=t.content)}else if(3===t.nodeType){const e=t.data;if(e.indexOf(a)>=0){const s=t.parentNode,o=e.split(h),r=o.length-1;for(let e=0;e<r;e++){let i,r=o[e];if(""===r)i=m();else{const t=f.exec(r);null!==t&&d(t[2],c)&&(r=r.slice(0,t.index)+t[1]+t[2].slice(0,-c.length)+t[3]),i=document.createTextNode(r)}s.insertBefore(i,t),this.parts.push({type:"node",index:++n})}""===o[r]?(s.insertBefore(m(),t),i.push(t)):t.data=o[r],p+=r}}else if(8===t.nodeType)if(t.data===a){const e=t.parentNode;null!==t.previousSibling&&n!==r||(n++,e.insertBefore(m(),t)),r=n,this.parts.push({type:"node",index:n}),null===t.nextSibling?t.data="":(i.push(t),n--),p++}else{let e=-1;for(;-1!==(e=t.data.indexOf(a,e+1));)this.parts.push({type:"node",index:-1}),p++}}else o.currentNode=s.pop()}for(const t of i)t.parentNode.removeChild(t)}}const d=(t,e)=>{const i=t.length-e.length;return i>=0&&t.slice(i)===e},u=t=>-1!==t.index,m=()=>document.createComment(""),f=/([ \x09\x0a\x0c\x0d])([^\0-\x1F\x7F-\x9F "'>=\/]+)([ \x09\x0a\x0c\x0d]*=[ \x09\x0a\x0c\x0d]*(?:[^ \x09\x0a\x0c\x0d"'`<>=]*|"[^"]*|'[^']*))$/;class g{constructor(t,e,i){this.__parts=[],this.template=t,this.processor=e,this.options=i}update(t){let e=0;for(const i of this.__parts)void 0!==i&&i.setValue(t[e]),e++;for(const t of this.__parts)void 0!==t&&t.commit()}_clone(){const t=s?this.template.element.content.cloneNode(!0):document.importNode(this.template.element.content,!0),e=[],i=this.template.parts,o=document.createTreeWalker(t,133,null,!1);let r,n=0,a=0,p=o.nextNode();for(;n<i.length;)if(r=i[n],u(r)){for(;a<r.index;)a++,"TEMPLATE"===p.nodeName&&(e.push(p),o.currentNode=p.content),null===(p=o.nextNode())&&(o.currentNode=e.pop(),p=o.nextNode());if("node"===r.type){const t=this.processor.handleTextExpression(this.options);t.insertAfterNode(p.previousSibling),this.__parts.push(t)}else this.__parts.push(...this.processor.handleAttributeExpressions(p,r.name,r.strings,this.options));n++}else this.__parts.push(void 0),n++;return s&&(document.adoptNode(t),customElements.upgrade(t)),t}}const y=` ${a} `;class _{constructor(t,e,i,s){this.strings=t,this.values=e,this.type=i,this.processor=s}getHTML(){const t=this.strings.length-1;let e="",i=!1;for(let s=0;s<t;s++){const t=this.strings[s],o=t.lastIndexOf("\x3c!--");i=(o>-1||i)&&-1===t.indexOf("--\x3e",o+1);const r=f.exec(t);e+=null===r?t+(i?y:p):t.substr(0,r.index)+r[1]+r[2]+c+r[3]+a}return e+=this.strings[t]}getTemplateElement(){const t=document.createElement("template");return t.innerHTML=this.getHTML(),t}}const v=t=>null===t||!("object"==typeof t||"function"==typeof t),b=t=>Array.isArray(t)||!(!t||!t[Symbol.iterator]);class w{constructor(t,e,i){this.dirty=!0,this.element=t,this.name=e,this.strings=i,this.parts=[];for(let t=0;t<i.length-1;t++)this.parts[t]=this._createPart()}_createPart(){return new S(this)}_getValue(){const t=this.strings,e=t.length-1;let i="";for(let s=0;s<e;s++){i+=t[s];const e=this.parts[s];if(void 0!==e){const t=e.value;if(v(t)||!b(t))i+="string"==typeof t?t:String(t);else for(const e of t)i+="string"==typeof e?e:String(e)}}return i+=t[e]}commit(){this.dirty&&(this.dirty=!1,this.element.setAttribute(this.name,this._getValue()))}}class S{constructor(t){this.value=void 0,this.committer=t}setValue(t){t===r||v(t)&&t===this.value||(this.value=t,i(t)||(this.committer.dirty=!0))}commit(){for(;i(this.value);){const t=this.value;this.value=r,t(this)}this.value!==r&&this.committer.commit()}}class x{constructor(t){this.value=void 0,this.__pendingValue=void 0,this.options=t}appendInto(t){this.startNode=t.appendChild(m()),this.endNode=t.appendChild(m())}insertAfterNode(t){this.startNode=t,this.endNode=t.nextSibling}appendIntoPart(t){t.__insert(this.startNode=m()),t.__insert(this.endNode=m())}insertAfterPart(t){t.__insert(this.startNode=m()),this.endNode=t.endNode,t.endNode=this.startNode}setValue(t){this.__pendingValue=t}commit(){for(;i(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=r,t(this)}const t=this.__pendingValue;t!==r&&(v(t)?t!==this.value&&this.__commitText(t):t instanceof _?this.__commitTemplateResult(t):t instanceof Node?this.__commitNode(t):b(t)?this.__commitIterable(t):t===n?(this.value=n,this.clear()):this.__commitText(t))}__insert(t){this.endNode.parentNode.insertBefore(t,this.endNode)}__commitNode(t){this.value!==t&&(this.clear(),this.__insert(t),this.value=t)}__commitText(t){const e=this.startNode.nextSibling,i="string"==typeof(t=null==t?"":t)?t:String(t);e===this.endNode.previousSibling&&3===e.nodeType?e.data=i:this.__commitNode(document.createTextNode(i)),this.value=t}__commitTemplateResult(t){const e=this.options.templateFactory(t);if(this.value instanceof g&&this.value.template===e)this.value.update(t.values);else{const i=new g(e,t.processor,this.options),s=i._clone();i.update(t.values),this.__commitNode(s),this.value=i}}__commitIterable(t){Array.isArray(this.value)||(this.value=[],this.clear());const e=this.value;let i,s=0;for(const o of t)void 0===(i=e[s])&&(i=new x(this.options),e.push(i),0===s?i.appendIntoPart(this):i.insertAfterPart(e[s-1])),i.setValue(o),i.commit(),s++;s<e.length&&(e.length=s,this.clear(i&&i.endNode))}clear(t=this.startNode){o(this.startNode.parentNode,t.nextSibling,this.endNode)}}class P{constructor(t,e,i){if(this.value=void 0,this.__pendingValue=void 0,2!==i.length||""!==i[0]||""!==i[1])throw new Error("Boolean attributes can only contain a single expression");this.element=t,this.name=e,this.strings=i}setValue(t){this.__pendingValue=t}commit(){for(;i(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=r,t(this)}if(this.__pendingValue===r)return;const t=!!this.__pendingValue;this.value!==t&&(t?this.element.setAttribute(this.name,""):this.element.removeAttribute(this.name),this.value=t),this.__pendingValue=r}}class $ extends w{constructor(t,e,i){super(t,e,i),this.single=2===i.length&&""===i[0]&&""===i[1]}_createPart(){return new k(this)}_getValue(){return this.single?this.parts[0].value:super._getValue()}commit(){this.dirty&&(this.dirty=!1,this.element[this.name]=this._getValue())}}class k extends S{}let C=!1;try{const t={get capture(){return C=!0,!1}};window.addEventListener("test",t,t),window.removeEventListener("test",t,t)}catch(t){}class N{constructor(t,e,i){this.value=void 0,this.__pendingValue=void 0,this.element=t,this.eventName=e,this.eventContext=i,this.__boundHandleEvent=(t=>this.handleEvent(t))}setValue(t){this.__pendingValue=t}commit(){for(;i(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=r,t(this)}if(this.__pendingValue===r)return;const t=this.__pendingValue,e=this.value,s=null==t||null!=e&&(t.capture!==e.capture||t.once!==e.once||t.passive!==e.passive),o=null!=t&&(null==e||s);s&&this.element.removeEventListener(this.eventName,this.__boundHandleEvent,this.__options),o&&(this.__options=A(t),this.element.addEventListener(this.eventName,this.__boundHandleEvent,this.__options)),this.value=t,this.__pendingValue=r}handleEvent(t){"function"==typeof this.value?this.value.call(this.eventContext||this.element,t):this.value.handleEvent(t)}}const A=t=>t&&(C?{capture:t.capture,passive:t.passive,once:t.once}:t.capture);const T=new class{handleAttributeExpressions(t,e,i,s){const o=e[0];return"."===o?new $(t,e.slice(1),i).parts:"@"===o?[new N(t,e.slice(1),s.eventContext)]:"?"===o?[new P(t,e.slice(1),i)]:new w(t,e,i).parts}handleTextExpression(t){return new x(t)}};function z(t){let e=R.get(t.type);void 0===e&&(e={stringsArray:new WeakMap,keyString:new Map},R.set(t.type,e));let i=e.stringsArray.get(t.strings);if(void 0!==i)return i;const s=t.strings.join(a);return void 0===(i=e.keyString.get(s))&&(i=new l(t,t.getTemplateElement()),e.keyString.set(s,i)),e.stringsArray.set(t.strings,i),i}const R=new Map,E=new WeakMap;(window.litHtmlVersions||(window.litHtmlVersions=[])).push("1.1.2");const U=(t,...e)=>new _(t,e,"html",T),O=133;function M(t,e){const{element:{content:i},parts:s}=t,o=document.createTreeWalker(i,O,null,!1);let r=q(s),n=s[r],a=-1,p=0;const h=[];let c=null;for(;o.nextNode();){a++;const t=o.currentNode;for(t.previousSibling===c&&(c=null),e.has(t)&&(h.push(t),null===c&&(c=t)),null!==c&&p++;void 0!==n&&n.index===a;)n.index=null!==c?-1:n.index-p,n=s[r=q(s,r)]}h.forEach(t=>t.parentNode.removeChild(t))}const V=t=>{let e=11===t.nodeType?0:1;const i=document.createTreeWalker(t,O,null,!1);for(;i.nextNode();)e++;return e},q=(t,e=-1)=>{for(let i=e+1;i<t.length;i++){const e=t[i];if(u(e))return i}return-1};const I=(t,e)=>`${t}--${e}`;let j=!0;void 0===window.ShadyCSS?j=!1:void 0===window.ShadyCSS.prepareTemplateDom&&(console.warn("Incompatible ShadyCSS version detected. Please update to at least @webcomponents/webcomponentsjs@2.0.2 and @webcomponents/shadycss@1.3.1."),j=!1);const W=t=>e=>{const i=I(e.type,t);let s=R.get(i);void 0===s&&(s={stringsArray:new WeakMap,keyString:new Map},R.set(i,s));let o=s.stringsArray.get(e.strings);if(void 0!==o)return o;const r=e.strings.join(a);if(void 0===(o=s.keyString.get(r))){const i=e.getTemplateElement();j&&window.ShadyCSS.prepareTemplateDom(i,t),o=new l(e,i),s.keyString.set(r,o)}return s.stringsArray.set(e.strings,o),o},B=["html","svg"],H=new Set,F=(t,e,i)=>{H.add(t);const s=i?i.element:document.createElement("template"),o=e.querySelectorAll("style"),{length:r}=o;if(0===r)return void window.ShadyCSS.prepareTemplateStyles(s,t);const n=document.createElement("style");for(let t=0;t<r;t++){const e=o[t];e.parentNode.removeChild(e),n.textContent+=e.textContent}(t=>{B.forEach(e=>{const i=R.get(I(e,t));void 0!==i&&i.keyString.forEach(t=>{const{element:{content:e}}=t,i=new Set;Array.from(e.querySelectorAll("style")).forEach(t=>{i.add(t)}),M(t,i)})})})(t);const a=s.content;i?function(t,e,i=null){const{element:{content:s},parts:o}=t;if(null==i)return void s.appendChild(e);const r=document.createTreeWalker(s,O,null,!1);let n=q(o),a=0,p=-1;for(;r.nextNode();)for(p++,r.currentNode===i&&(a=V(e),i.parentNode.insertBefore(e,i));-1!==n&&o[n].index===p;){if(a>0){for(;-1!==n;)o[n].index+=a,n=q(o,n);return}n=q(o,n)}}(i,n,a.firstChild):a.insertBefore(n,a.firstChild),window.ShadyCSS.prepareTemplateStyles(s,t);const p=a.querySelector("style");if(window.ShadyCSS.nativeShadow&&null!==p)e.insertBefore(p.cloneNode(!0),e.firstChild);else if(i){a.insertBefore(n,a.firstChild);const t=new Set;t.add(n),M(i,t)}},L=(t,e,i)=>{if(!i||"object"!=typeof i||!i.scopeName)throw new Error("The `scopeName` option is required.");const s=i.scopeName,r=E.has(e),n=j&&11===e.nodeType&&!!e.host,a=n&&!H.has(s),p=a?document.createDocumentFragment():e;if(((t,e,i)=>{let s=E.get(e);void 0===s&&(o(e,e.firstChild),E.set(e,s=new x(Object.assign({templateFactory:z},i))),s.appendInto(e)),s.setValue(t),s.commit()})(t,p,Object.assign({templateFactory:W(s)},i)),a){const t=E.get(p);E.delete(p);const i=t.value instanceof g?t.value.template:void 0;F(s,p,i),o(e,e.firstChild),e.appendChild(p),E.set(e,t)}!r&&n&&window.ShadyCSS.styleElement(e.host)};window.JSCompiler_renameProperty=((t,e)=>t);const D={toAttribute(t,e){switch(e){case Boolean:return t?"":null;case Object:case Array:return null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){switch(e){case Boolean:return null!==t;case Number:return null===t?null:Number(t);case Object:case Array:return JSON.parse(t)}return t}},J=(t,e)=>e!==t&&(e==e||t==t),G={attribute:!0,type:String,converter:D,reflect:!1,hasChanged:J},Z=Promise.resolve(!0),K=1,Q=4,X=8,Y=16,tt=32,et="finalized";class it extends HTMLElement{constructor(){super(),this._updateState=0,this._instanceProperties=void 0,this._updatePromise=Z,this._hasConnectedResolver=void 0,this._changedProperties=new Map,this._reflectingProperties=void 0,this.initialize()}static get observedAttributes(){this.finalize();const t=[];return this._classProperties.forEach((e,i)=>{const s=this._attributeNameForProperty(i,e);void 0!==s&&(this._attributeToPropertyMap.set(s,i),t.push(s))}),t}static _ensureClassProperties(){if(!this.hasOwnProperty(JSCompiler_renameProperty("_classProperties",this))){this._classProperties=new Map;const t=Object.getPrototypeOf(this)._classProperties;void 0!==t&&t.forEach((t,e)=>this._classProperties.set(e,t))}}static createProperty(t,e=G){if(this._ensureClassProperties(),this._classProperties.set(t,e),e.noAccessor||this.prototype.hasOwnProperty(t))return;const i="symbol"==typeof t?Symbol():`__${t}`;Object.defineProperty(this.prototype,t,{get(){return this[i]},set(e){const s=this[t];this[i]=e,this._requestUpdate(t,s)},configurable:!0,enumerable:!0})}static finalize(){const t=Object.getPrototypeOf(this);if(t.hasOwnProperty(et)||t.finalize(),this[et]=!0,this._ensureClassProperties(),this._attributeToPropertyMap=new Map,this.hasOwnProperty(JSCompiler_renameProperty("properties",this))){const t=this.properties,e=[...Object.getOwnPropertyNames(t),..."function"==typeof Object.getOwnPropertySymbols?Object.getOwnPropertySymbols(t):[]];for(const i of e)this.createProperty(i,t[i])}}static _attributeNameForProperty(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}static _valueHasChanged(t,e,i=J){return i(t,e)}static _propertyValueFromAttribute(t,e){const i=e.type,s=e.converter||D,o="function"==typeof s?s:s.fromAttribute;return o?o(t,i):t}static _propertyValueToAttribute(t,e){if(void 0===e.reflect)return;const i=e.type,s=e.converter;return(s&&s.toAttribute||D.toAttribute)(t,i)}initialize(){this._saveInstanceProperties(),this._requestUpdate()}_saveInstanceProperties(){this.constructor._classProperties.forEach((t,e)=>{if(this.hasOwnProperty(e)){const t=this[e];delete this[e],this._instanceProperties||(this._instanceProperties=new Map),this._instanceProperties.set(e,t)}})}_applyInstanceProperties(){this._instanceProperties.forEach((t,e)=>this[e]=t),this._instanceProperties=void 0}connectedCallback(){this._updateState=this._updateState|tt,this._hasConnectedResolver&&(this._hasConnectedResolver(),this._hasConnectedResolver=void 0)}disconnectedCallback(){}attributeChangedCallback(t,e,i){e!==i&&this._attributeToProperty(t,i)}_propertyToAttribute(t,e,i=G){const s=this.constructor,o=s._attributeNameForProperty(t,i);if(void 0!==o){const t=s._propertyValueToAttribute(e,i);if(void 0===t)return;this._updateState=this._updateState|X,null==t?this.removeAttribute(o):this.setAttribute(o,t),this._updateState=this._updateState&~X}}_attributeToProperty(t,e){if(this._updateState&X)return;const i=this.constructor,s=i._attributeToPropertyMap.get(t);if(void 0!==s){const t=i._classProperties.get(s)||G;this._updateState=this._updateState|Y,this[s]=i._propertyValueFromAttribute(e,t),this._updateState=this._updateState&~Y}}_requestUpdate(t,e){let i=!0;if(void 0!==t){const s=this.constructor,o=s._classProperties.get(t)||G;s._valueHasChanged(this[t],e,o.hasChanged)?(this._changedProperties.has(t)||this._changedProperties.set(t,e),!0!==o.reflect||this._updateState&Y||(void 0===this._reflectingProperties&&(this._reflectingProperties=new Map),this._reflectingProperties.set(t,o))):i=!1}!this._hasRequestedUpdate&&i&&this._enqueueUpdate()}requestUpdate(t,e){return this._requestUpdate(t,e),this.updateComplete}async _enqueueUpdate(){let t,e;this._updateState=this._updateState|Q;const i=this._updatePromise;this._updatePromise=new Promise((i,s)=>{t=i,e=s});try{await i}catch(t){}this._hasConnected||await new Promise(t=>this._hasConnectedResolver=t);try{const t=this.performUpdate();null!=t&&await t}catch(t){e(t)}t(!this._hasRequestedUpdate)}get _hasConnected(){return this._updateState&tt}get _hasRequestedUpdate(){return this._updateState&Q}get hasUpdated(){return this._updateState&K}performUpdate(){this._instanceProperties&&this._applyInstanceProperties();let t=!1;const e=this._changedProperties;try{(t=this.shouldUpdate(e))&&this.update(e)}catch(e){throw t=!1,e}finally{this._markUpdated()}t&&(this._updateState&K||(this._updateState=this._updateState|K,this.firstUpdated(e)),this.updated(e))}_markUpdated(){this._changedProperties=new Map,this._updateState=this._updateState&~Q}get updateComplete(){return this._getUpdateComplete()}_getUpdateComplete(){return this._updatePromise}shouldUpdate(t){return!0}update(t){void 0!==this._reflectingProperties&&this._reflectingProperties.size>0&&(this._reflectingProperties.forEach((t,e)=>this._propertyToAttribute(e,this[e],t)),this._reflectingProperties=void 0)}updated(t){}firstUpdated(t){}}it[et]=!0;const st=t=>e=>"function"==typeof e?((t,e)=>(window.customElements.define(t,e),e))(t,e):((t,e)=>{const{kind:i,elements:s}=e;return{kind:i,elements:s,finisher(e){window.customElements.define(t,e)}}})(t,e),ot=(t,e)=>"method"!==e.kind||!e.descriptor||"value"in e.descriptor?{kind:"field",key:Symbol(),placement:"own",descriptor:{},initializer(){"function"==typeof e.initializer&&(this[e.key]=e.initializer.call(this))},finisher(i){i.createProperty(e.key,t)}}:Object.assign({},e,{finisher(i){i.createProperty(e.key,t)}}),rt=(t,e,i)=>{e.constructor.createProperty(i,t)};function nt(t){return(e,i)=>void 0!==i?rt(t,e,i):ot(t,e)}const at="adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,pt=Symbol();class ht{constructor(t,e){if(e!==pt)throw new Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t}get styleSheet(){return void 0===this._styleSheet&&(at?(this._styleSheet=new CSSStyleSheet,this._styleSheet.replaceSync(this.cssText)):this._styleSheet=null),this._styleSheet}toString(){return this.cssText}}const ct=(t,...e)=>{const i=e.reduce((e,i,s)=>e+(t=>{if(t instanceof ht)return t.cssText;if("number"==typeof t)return t;throw new Error(`Value passed to 'css' function must be a 'css' function result: ${t}. Use 'unsafeCSS' to pass non-literal values, but\n            take care to ensure page security.`)})(i)+t[s+1],t[0]);return new ht(i,pt)};(window.litElementVersions||(window.litElementVersions=[])).push("2.2.1");const lt=t=>t.flat?t.flat(1/0):function t(e,i=[]){for(let s=0,o=e.length;s<o;s++){const o=e[s];Array.isArray(o)?t(o,i):i.push(o)}return i}(t);class dt extends it{static finalize(){super.finalize.call(this),this._styles=this.hasOwnProperty(JSCompiler_renameProperty("styles",this))?this._getUniqueStyles():this._styles||[]}static _getUniqueStyles(){const t=this.styles,e=[];if(Array.isArray(t)){lt(t).reduceRight((t,e)=>(t.add(e),t),new Set).forEach(t=>e.unshift(t))}else t&&e.push(t);return e}initialize(){super.initialize(),this.renderRoot=this.createRenderRoot(),window.ShadowRoot&&this.renderRoot instanceof window.ShadowRoot&&this.adoptStyles()}createRenderRoot(){return this.attachShadow({mode:"open"})}adoptStyles(){const t=this.constructor._styles;0!==t.length&&(void 0===window.ShadyCSS||window.ShadyCSS.nativeShadow?at?this.renderRoot.adoptedStyleSheets=t.map(t=>t.styleSheet):this._needsShimAdoptedStyleSheets=!0:window.ShadyCSS.ScopingShim.prepareAdoptedCssText(t.map(t=>t.cssText),this.localName))}connectedCallback(){super.connectedCallback(),this.hasUpdated&&void 0!==window.ShadyCSS&&window.ShadyCSS.styleElement(this)}update(t){super.update(t);const e=this.render();e instanceof _&&this.constructor.render(e,this.renderRoot,{scopeName:this.localName,eventContext:this}),this._needsShimAdoptedStyleSheets&&(this._needsShimAdoptedStyleSheets=!1,this.constructor._styles.forEach(t=>{const e=document.createElement("style");e.textContent=t.cssText,this.renderRoot.appendChild(e)}))}render(){}}dt.finalized=!0,dt.render=L;const ut=(t,e)=>{history.replaceState(null,"",e)},mt=ct`
    :host {
      @apply --paper-font-body1;
    }

    app-header-layout,
    ha-app-layout {
      background-color: var(--primary-background-color);
    }

    app-header, app-toolbar {
      background-color: var(--primary-color);
      font-weight: 400;
      color: var(--text-primary-color, white);
    }

    app-toolbar ha-menu-button + [main-title],
    app-toolbar ha-paper-icon-button-arrow-prev + [main-title],
    app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }

    button.link {
      background: none;
      color: inherit;
      border: none;
      padding: 0;
      font: inherit;
      text-align: left;
      text-decoration: underline;
      cursor: pointer;
    }

    .card-actions a {
      text-decoration: none;
    }

    .card-actions .warning {
      --mdc-theme-primary: var(--google-red-500);
    }
`,ft=ct`
    :host {
      font-family: var(--paper-font-body1_-_font-family); -webkit-font-smoothing: var(--paper-font-body1_-_-webkit-font-smoothing); font-size: var(--paper-font-body1_-_font-size); font-weight: var(--paper-font-body1_-_font-weight); line-height: var(--paper-font-body1_-_line-height);
    }

    app-header-layout, ha-app-layout {
      background-color: var(--primary-background-color);
    }

    app-header, app-toolbar, paper-tabs {
      background-color: var(--primary-color);
      font-weight: 400;
      text-transform: uppercase;
      color: var(--text-primary-color, white);
    }

    paper-tabs {
      --paper-tabs-selection-bar-color: #fff;
      margin-left: 12px;
    }

    app-toolbar ha-menu-button + [main-title], app-toolbar ha-paper-icon-button-arrow-prev + [main-title], app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }
`,gt=ct`
    :host {
        --hacs-status-installed: #126e15;
        --hacs-status-pending-restart: #a70000;
        --hacs-status-pending-update: #ffab40;
        --hacs-status-default: var(--primary-text-color);
        --hacs-badge-color: var(--primary-color);
        --hacs-badge-text-color: var(--primary-text-color);
      }
`,yt=[mt,ft,ct`
    :root {
        font-family: var(--paper-font-body1_-_font-family);
        -webkit-font-smoothing: var(--paper-font-body1_-_-webkit-font-smoothing);
        font-size: var(--paper-font-body1_-_font-size);
        font-weight: var(--paper-font-body1_-_font-weight);
        line-height: var(--paper-font-body1_-_line-height);
    }
    a {
        text-decoration: none;
        color: var(--dark-primary-color);
    }
    h1 {
        font-family: var(--paper-font-title_-_font-family);
        -webkit-font-smoothing: var(--paper-font-title_-_-webkit-font-smoothing);
        white-space: var(--paper-font-title_-_white-space);
        overflow: var(--paper-font-title_-_overflow);
        text-overflow: var(--paper-font-title_-_text-overflow);
        font-size: var(--paper-font-title_-_font-size);
        font-weight: var(--paper-font-title_-_font-weight);
        line-height: var(--paper-font-title_-_line-height);
        @apply --paper-font-title;
    }
    .title {
        margin-bottom: 16px;
        padding-top: 4px;
        color: var(--primary-text-color);
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
    }
    .addition {
        color: var(--secondary-text-color);
        position: relative;
        height: auto;
        line-height: 1.2em;
        text-overflow: ellipsis;
        overflow: hidden;
    }
    paper-card {
        cursor: pointer;
    }
    ha-card {
      margin: 8px;
    }
    ha-icon {
        margin-right: 16px;
        float: left;
        color: var(--primary-text-color);
    }
      ha-icon.installed {
        color: var(--hacs-status-installed);
    }
      ha-icon.pending-upgrade {
        color: var(--hacs-status-pending-update);
    }
      ha-icon.pending-restart {
        color: var(--hacs-status-pending-restart);
    }
`,gt],_t=t=>null!==t,vt=t=>t?"":null,bt=(t,e)=>e!==t&&(e==e||t==t),wt={attribute:!0,type:String,reflect:!1,hasChanged:bt},St=new Promise(t=>t(!0)),xt=1,Pt=4,$t=8;class kt extends HTMLElement{constructor(){super(),this._updateState=0,this._instanceProperties=void 0,this._updatePromise=St,this._changedProperties=new Map,this._reflectingProperties=void 0,this.initialize()}static get observedAttributes(){this._finalize();const t=[];for(const[e,i]of this._classProperties){const s=this._attributeNameForProperty(e,i);void 0!==s&&(this._attributeToPropertyMap.set(s,e),t.push(s))}return t}static createProperty(t,e=wt){if(!this.hasOwnProperty("_classProperties")){this._classProperties=new Map;const t=Object.getPrototypeOf(this)._classProperties;void 0!==t&&t.forEach((t,e)=>this._classProperties.set(e,t))}if(this._classProperties.set(t,e),this.prototype.hasOwnProperty(t))return;const i="symbol"==typeof t?Symbol():`__${t}`;Object.defineProperty(this.prototype,t,{get(){return this[i]},set(s){const o=this[t];this[i]=s,this._requestPropertyUpdate(t,o,e)},configurable:!0,enumerable:!0})}static _finalize(){if(this.hasOwnProperty("_finalized")&&this._finalized)return;const t=Object.getPrototypeOf(this);"function"==typeof t._finalize&&t._finalize(),this._finalized=!0,this._attributeToPropertyMap=new Map;const e=this.properties,i=[...Object.getOwnPropertyNames(e),..."function"==typeof Object.getOwnPropertySymbols?Object.getOwnPropertySymbols(e):[]];for(const t of i)this.createProperty(t,e[t])}static _attributeNameForProperty(t,e){const i=void 0!==e&&e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}static _valueHasChanged(t,e,i=bt){return i(t,e)}static _propertyValueFromAttribute(t,e){const i=e&&e.type;if(void 0===i)return t;const s=i===Boolean?_t:"function"==typeof i?i:i.fromAttribute;return s?s(t):t}static _propertyValueToAttribute(t,e){if(void 0===e||void 0===e.reflect)return;return(e.type===Boolean?vt:e.type&&e.type.toAttribute||String)(t)}initialize(){this.renderRoot=this.createRenderRoot(),this._saveInstanceProperties()}_saveInstanceProperties(){for(const[t]of this.constructor._classProperties)if(this.hasOwnProperty(t)){const e=this[t];delete this[t],this._instanceProperties||(this._instanceProperties=new Map),this._instanceProperties.set(t,e)}}_applyInstanceProperties(){for(const[t,e]of this._instanceProperties)this[t]=e;this._instanceProperties=void 0}createRenderRoot(){return this.attachShadow({mode:"open"})}connectedCallback(){this._updateState&xt?void 0!==window.ShadyCSS&&window.ShadyCSS.styleElement(this):this.requestUpdate()}disconnectedCallback(){}attributeChangedCallback(t,e,i){e!==i&&this._attributeToProperty(t,i)}_propertyToAttribute(t,e,i=wt){const s=this.constructor,o=s._propertyValueToAttribute(e,i);if(void 0!==o){const e=s._attributeNameForProperty(t,i);void 0!==e&&(this._updateState=this._updateState|$t,null===o?this.removeAttribute(e):this.setAttribute(e,o),this._updateState=this._updateState&~$t)}}_attributeToProperty(t,e){if(!(this._updateState&$t)){const i=this.constructor,s=i._attributeToPropertyMap.get(t);if(void 0!==s){const t=i._classProperties.get(s);this[s]=i._propertyValueFromAttribute(e,t)}}}requestUpdate(t,e){if(void 0!==t){const i=this.constructor._classProperties.get(t)||wt;return this._requestPropertyUpdate(t,e,i)}return this._invalidate()}_requestPropertyUpdate(t,e,i){return this.constructor._valueHasChanged(this[t],e,i.hasChanged)?(this._changedProperties.has(t)||this._changedProperties.set(t,e),!0===i.reflect&&(void 0===this._reflectingProperties&&(this._reflectingProperties=new Map),this._reflectingProperties.set(t,i)),this._invalidate()):this.updateComplete}async _invalidate(){if(!this._hasRequestedUpdate){let t;this._updateState=this._updateState|Pt;const e=this._updatePromise;this._updatePromise=new Promise(e=>t=e),await e,this._validate(),t(!this._hasRequestedUpdate)}return this.updateComplete}get _hasRequestedUpdate(){return this._updateState&Pt}_validate(){if(this._instanceProperties&&this._applyInstanceProperties(),this.shouldUpdate(this._changedProperties)){const t=this._changedProperties;this.update(t),this._markUpdated(),this._updateState&xt||(this._updateState=this._updateState|xt,this.firstUpdated(t)),this.updated(t)}else this._markUpdated()}_markUpdated(){this._changedProperties=new Map,this._updateState=this._updateState&~Pt}get updateComplete(){return this._updatePromise}shouldUpdate(t){return!0}update(t){if(void 0!==this._reflectingProperties&&this._reflectingProperties.size>0){for(const[t,e]of this._reflectingProperties)this._propertyToAttribute(t,this[t],e);this._reflectingProperties=void 0}}updated(t){}firstUpdated(t){}}kt._attributeToPropertyMap=new Map,kt._finalized=!0,kt._classProperties=new Map,kt.properties={};class Ct extends kt{update(t){super.update(t);const e=this.render();e instanceof _&&this.constructor.render(e,this.renderRoot,{scopeName:this.localName,eventContext:this})}render(){}}Ct.render=L;window.customElements.define("granite-spinner",class extends Ct{static get properties(){return{active:{type:Boolean,reflect:!0},hover:{type:Boolean,reflect:!0},size:{type:Number},color:{type:String},lineWidth:{type:String},containerHeight:{type:Number,value:150},debug:{type:Boolean}}}constructor(){super(),this.size=100,this.color="#28b6d8",this.lineWidth="1.5em",this.containerHeight=150}firstUpdated(){this.debug&&console.log("[granite-spinner] firstUpdated")}shouldUpdate(){return this.debug&&console.log("[granite-spinner] shouldUpdate",this.lineWidth),!0}render(){if(this.active)return U`
      ${this._renderStyles()}      
      <div id="spinner-container">
        <div id="spinner" class="loading">
        </div>
      </div>
    `}_renderStyles(){return U`
      <style>
        @charset "UTF-8";

        /**
        @license MIT
        Copyright (c) 2015 Horacio "LostInBrittany" Gonzalez
        */
        
        :host {
          display: inline-block;
          position: relative;
          width:100%;
        }
        #spinner-container {
          display: flex;
          justify-content: center;
          align-items: center;
          position: relative;
          width:100%;

          position: ${this.hover?"absolute":"relative"};
          min-width: ${this.size}px;
          min-height: ${this.size}px;
          height: ${Math.max(this.size,this.containerHeight,200)}px;
        }
        #spinner {
          margin: 60px auto;
          font-size: 10px;
          position: relative;
          text-indent: -9999em;
        
          border: 1.5em solid rgba(210,210,210, 1);
          border-left: 1.5em solid #28b6d8;
          -webkit-transform: translateZ(0);
          -ms-transform: translateZ(0);
          transform: translateZ(0);
          -webkit-animation: load8 1.25s infinite linear;
          animation: load8 1.25s infinite linear;          
          
          border-left-color: ${this.color};
          border-width: ${this.lineWidth};
        }
        
        #spinner,
        #spinner:after {
          border-radius: 50%;
          width: ${this.size?`${this.size}px`:"10em"};
          height: ${this.size?`${this.size}px`:"10em"};
        }

        @-webkit-keyframes load8 {
          0% {
            -webkit-transform: rotate(0deg);
            transform: rotate(0deg);
          }
          100% {
            -webkit-transform: rotate(360deg);
            transform: rotate(360deg);
          }
        }
        @keyframes load8 {
          0% {
            -webkit-transform: rotate(0deg);
            transform: rotate(0deg);
          }
          100% {
            -webkit-transform: rotate(360deg);
            transform: rotate(360deg);
          }
        }      

      </style>
      
    `}});let Nt=class extends dt{render(){return U`
            <granite-spinner
                color="var(--primary-color)"
                active hover
                size=400
                containerHeight=100%
                >
            </granite-spinner>
            `}};Nt=t([st("hacs-spinner")],Nt);let At=class extends dt{constructor(){super(...arguments),this.repository_view=!1}render(){if("repository"===this.panel)return U`
      <hacs-panel-repository
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .repository=${this.repository}
      >
      </hacs-panel-repository>`;{const e=this.panel,i=this.configuration;var t=this.repositories||[];return t=this.repositories.filter(function(t){if("installed"!==e){if("172733314"===t.id)return!1;if(t.hide)return!1;if(null!==i.country&&i.country!==t.country)return!1}else if(t.installed)return!0;return t.category===e}),U`
      <div>
        <paper-input
            class="search-bar"
            type="text"
            id="Search"
            @input=${this.DoSearch}
            placeholder="  Please enter a search term.."
            autofocus
        ></paper-input>
      </div>
    <div class="card-group">
    ${t.sort((t,e)=>t.name>e.name?1:-1).map(t=>U`

      <paper-card id="${t.id}" @click="${this.ShowRepository}" .RepoID="${t.id}">
      <div class="card-content">
        <div>
          <ha-icon
            icon="mdi:cube"
            class="${t.status}"
            title="${t.status_description}"
            >
          </ha-icon>
          <div>
            <div class="title">${t.name}</div>
            <div class="addition">${t.description}</div>
          </div>
        </div>
      </div>
      </paper-card>
      `)}
    </div>
          `}}DoSearch(t){var e=t.path[0].value.ToLowerCase();console.log("Search is currently not working, you wanted:",e)}ShowRepository(t){t.path.forEach(t=>{void 0!==t.RepoID&&(this.panel="repository",this.repository=t.RepoID,this.repository_view=!0,this.requestUpdate(),ut(0,`/hacs/repository/${t.RepoID}`))})}static get styles(){return[yt,ct`
        .search-bar {
          width: 92%;
          margin-left: 3.4%;
          margin-top: 2%;
          background-color: var(--primary-background-color);
          color: var(--primary-text-color);
          line-height: 32px;
          border-color: var(--dark-primary-color);
          border-width: inherit;
          border-bottom-width: thin;
      }
        .card-group {
          margin-top: 24px;
          width: 95%;
          margin-left: 2.5%;
        }

        .card-group .title {
          color: var(--primary-text-color);
          margin-bottom: 12px;
        }

        .card-group .description {
          font-size: 0.5em;
          font-weight: 500;
          margin-top: 4px;
        }

        .card-group paper-card {
          --card-group-columns: 4;
          width: calc((100% - 12px * var(--card-group-columns)) / var(--card-group-columns));
          margin: 4px;
          vertical-align: top;
          height: 136px;
        }

        @media screen and (max-width: 1200px) and (min-width: 901px) {
          .card-group paper-card {
            --card-group-columns: 3;
          }
        }

        @media screen and (max-width: 900px) and (min-width: 601px) {
          .card-group paper-card {
            --card-group-columns: 2;
          }
        }

        @media screen and (max-width: 600px) and (min-width: 0) {
          .card-group paper-card {
            width: 100%;
            margin: 4px 0;
          }
          .content {
            padding: 0;
          }
        }
    `]}};t([nt()],At.prototype,"hass",void 0),t([nt()],At.prototype,"repositories",void 0),t([nt()],At.prototype,"configuration",void 0),t([nt()],At.prototype,"panel",void 0),t([nt()],At.prototype,"repository_view",void 0),t([nt()],At.prototype,"repository",void 0),At=t([st("hacs-panel")],At);let Tt=class extends dt{render(){return console.log("hass: ",this.hass),console.log("configuration: ",this.configuration),U`

    <ha-card header="${this.hass.localize("component.hacs.config.title")}">
      <div class="card content">



      </div>
    </ha-card>
          `}static get styles(){return[yt]}};t([nt()],Tt.prototype,"hass",void 0),t([nt()],Tt.prototype,"repositories",void 0),t([nt()],Tt.prototype,"configuration",void 0),Tt=t([st("hacs-panel-settings")],Tt);const zt=new WeakMap,Rt=(t=>(...i)=>{const s=t(...i);return e.set(s,!0),s})(t=>e=>{if(!(e instanceof x))throw new Error("unsafeHTML can only be used in text bindings");const i=zt.get(e);if(void 0!==i&&v(t)&&t===i.value&&e.value===i.fragment)return;const s=document.createElement("template");s.innerHTML=t;const o=document.importNode(s.content,!0);e.setValue(o),zt.set(e,{value:t,fragment:o})});let Et=class extends dt{constructor(){super(...arguments),this.repository_view=!1}RepositoryWebSocketAction(t){this.hass.connection.sendMessagePromise({type:"hacs/repository",action:t,repository:this.repository}).then(t=>{this.repositories=t},t=>{console.error("Message failed!",t)}),this.requestUpdate()}firstUpdated(){this.repo.updated_info||this.RepositoryWebSocketAction("update")}render(){if(void 0===this.repository)return U`
      <hacs-panel
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .panel=${this.panel}
      .repository_view=${this.repository_view}
      .repository=${this.repository}
      >
      </hacs-panel>
      `;var t=this.repository,e=this.repositories;if(e=this.repositories.filter(function(e){return e.id===t}),this.repo=e[0],!this.repo.updated_info)return U`
    <hacs-spinner></hacs-spinner>
    <div class="loading">
      ${this.hass.localize("component.hacs.repository.loading")}
    </div>
    `;if(this.repo.installed)var i=`\n        ${this.hass.localize("component.hacs.repository.back_to")} ${this.hass.localize("component.hacs.repository.installed")}\n        `;else{if("appdaemon"===this.repo.category)var s="appdaemon_apps";else s=`${this.repo.category}s`;i=`\n        ${this.hass.localize("component.hacs.repository.back_to")} ${this.hass.localize(`component.hacs.common.${s}`)}\n        `}return U`

    <div class="getBack">
      <mwc-button @click=${this.GoBackToStore} title="${i}">
      <ha-icon  icon="mdi:arrow-left"></ha-icon>
        ${i}
      </mwc-button>
    </div>


    <ha-card header="${this.repo.name}">
      <paper-menu-button no-animations horizontal-align="right" role="group" aria-haspopup="true" vertical-align="top" aria-disabled="false">
        <paper-icon-button icon="hass:dots-vertical" slot="dropdown-trigger" role="button"></paper-icon-button>
        <paper-listbox slot="dropdown-content" role="listbox" tabindex="0">

        <paper-item @click=${this.RepositoryReload}>
        ${this.hass.localize("component.hacs.repository.update_information")}
        </paper-item>

      ${"version"===this.repo.version_or_commit?U`
      <paper-item @click=${this.RepositoryBeta}>
      ${this.repo.beta?this.hass.localize("component.hacs.repository.hide_beta"):this.hass.localize("component.hacs.repository.show_beta")}
        </paper-item>`:""}

        ${this.repo.custom?"":U`
        <paper-item @click=${this.RepositoryHide}>
          ${this.hass.localize("component.hacs.repository.hide")}
        </paper-item>`}

        <a href="https://google.com" rel='noreferrer' target="_blank">
          <paper-item>
            <ha-icon class="link-icon" icon="mdi:open-in-new"></ha-icon>
            ${this.hass.localize("component.hacs.repository.open_issue")}
          </paper-item>
        </a>

        <a href="https://google.com" rel='noreferrer' target="_blank">
          <paper-item>
            <ha-icon class="link-icon" icon="mdi:open-in-new"></ha-icon>
            ${this.hass.localize("component.hacs.repository.flag_this")}
          </paper-item>
        </a>

        </paper-listbox>
      </paper-menu-button>
      <div class="card-content">
        <div class="description addition">
          ${this.repo.description}
        </div>
        <div class="information">
          <div class="version installed">
            <b>${this.hass.localize("component.hacs.repository.installed")}: </b> ${this.repo.installed_version}
          </div>
          <div class="version available">
            <paper-dropdown-menu label="${this.hass.localize("component.hacs.repository.available")}">
              <paper-listbox slot="dropdown-content" selected="0">
                <paper-item>${this.repo.available_version}</paper-item>
                <paper-item>master</paper-item>
              </paper-listbox>
            </paper-dropdown-menu>
          </div>
        </div>
      </div>


      <div class="card-actions">

      <mwc-button @click=${this.RepositoryInstall}>
        ${this.hass.localize(`component.hacs.repository.${this.repo.main_action.toLowerCase()}`)}
      </mwc-button>

      ${this.repo.pending_upgrade?U`
      <a href="https://google.com" rel='noreferrer' target="_blank">
        <mwc-button>
        ${this.hass.localize("component.hacs.repository.changelog")}
        </mwc-button>
      </a>`:""}

        <a href="https://google.com" rel='noreferrer' target="_blank">
          <mwc-button>
          ${this.hass.localize("component.hacs.repository.repository")}
          </mwc-button>
        </a>

      ${this.repo.installed?U`
        <mwc-button class="right" @click=${this.RepositoryUnInstall}>
          ${this.hass.localize("component.hacs.repository.uninstall")}
        </mwc-button>`:""}


      </div>
    </ha-card>

    <ha-card>
      <div class="card-content">
        <div class="more_info">
          ${Rt(this.repo.additional_info)}
        </div>
      </div>
    </ha-card>
          `}RepositoryReload(){this.RepositoryWebSocketAction("update")}RepositoryInstall(){this.RepositoryWebSocketAction("install")}RepositoryUnInstall(){this.RepositoryWebSocketAction("uninstall")}RepositoryBeta(){this.repo.beta?this.RepositoryWebSocketAction("hide_beta"):this.RepositoryWebSocketAction("show_beta")}RepositoryHide(){this.repo.hide?this.RepositoryWebSocketAction("unhide"):this.RepositoryWebSocketAction("hide")}GoBackToStore(){this.repository=void 0,this.repo.installed?this.panel="installed":this.panel=this.repo.category,ut(0,`/hacs/${this.repo.category}`),this.requestUpdate()}static get styles(){return[yt,ct`
      .description {
        font-style: italic;
        padding-bottom: 16px;
      }
      .version {
        padding-bottom: 8px;
      }
      .options {
        float: right;
        width: 40%;
      }
      .information {
        width: 60%;
      }
      .getBack {
        margin-top: 8px;
        margin-bottom: 4px;
        margin-left: 5%;
      }
      .right {
        float: right;
      }
      .loading {
        text-align: center;
        width: 100%;
      }
      ha-card {
        width: 90%;
        margin-left: 5%;
      }
      .link-icon {
        color: var(--dark-primary-color);
        margin-right: 8px;
      }
      paper-menu-button {
        float: right;
        top: -65px;
      }
    `]}};t([nt()],Et.prototype,"hass",void 0),t([nt()],Et.prototype,"repositories",void 0),t([nt()],Et.prototype,"configuration",void 0),t([nt()],Et.prototype,"repository",void 0),t([nt()],Et.prototype,"panel",void 0),t([nt()],Et.prototype,"repository_view",void 0),Et=t([st("hacs-panel-repository")],Et);let Ut=class extends dt{constructor(){super(...arguments),this.repository_view=!1}getRepositories(){this.hass.connection.sendMessagePromise({type:"hacs/config"}).then(t=>{this.configuration=t},t=>{console.error("Message failed!",t)}),this.hass.connection.sendMessagePromise({type:"hacs/repositories"}).then(t=>{this.repositories=t},t=>{console.error("Message failed!",t)}),this.requestUpdate()}firstUpdated(){this.hass.connection.socket.onmessage=function(t){console.log(JSON.parse(t.data));var e=JSON.parse(t.data);e.event&&"hacs/repository"===e.event.event_type&&console.log(JSON.parse(t.data))},this.panel=this._page,this.getRepositories(),/repository\//i.test(this.panel)?(this.repository_view=!0,this.repository=this.panel.split("/")[1]):this.repository_view=!1,function(){if(customElements.get("hui-view"))return!0;const t=document.createElement("partial-panel-resolver");t.hass=document.querySelector("home-assistant").hass,t.route={path:"/lovelace/"};try{document.querySelector("home-assistant").appendChild(t).catch(t=>{})}catch(e){document.querySelector("home-assistant").removeChild(t)}customElements.get("hui-view")}()}render(){if(""===this.panel&&(ut(0,"/hacs/installed"),this.panel="installed"),void 0===this.repositories)return U`<hacs-spinner></hacs-spinner>`;/repository\//i.test(this.panel)?(this.repository_view=!0,this.repository=this.panel.split("/")[1],this.panel=this.panel.split("/")[0]):this.repository_view=!1;const t=this.panel;return U`
    <app-header-layout has-scrolling-region>
    <app-header slot="header" fixed>
        <app-toolbar>
        <ha-menu-button .hass="${this.hass}" .narrow="${this.narrow}"></ha-menu-button>
        <div main-title>${this.hass.localize("component.hacs.config.title")}</div>
        </app-toolbar>
    <paper-tabs
    scrollable
    attr-for-selected="page-name"
    .selected=${t}
    @iron-activate=${this.handlePageSelected}>

    <paper-tab page-name="installed">
    ${this.hass.localize("component.hacs.common.installed")}
    </paper-tab>

    <paper-tab page-name="integration">
    ${this.hass.localize("component.hacs.common.integrations")}
    </paper-tab>

    <paper-tab page-name="plugin">
    ${this.hass.localize("component.hacs.common.plugins")}
    </paper-tab>

    ${this.configuration.appdaemon?U`<paper-tab page-name="appdaemon">
        ${this.hass.localize("component.hacs.common.appdaemon_apps")}
    </paper-tab>`:""}

    ${this.configuration.python_script?U`<paper-tab page-name="python_script">
        ${this.hass.localize("component.hacs.common.python_scripts")}
    </paper-tab>`:""}

    ${this.configuration.theme?U`<paper-tab page-name="theme">
        ${this.hass.localize("component.hacs.common.themes")}
    </paper-tab>`:""}

    <paper-tab page-name="settings">
    ${this.hass.localize("component.hacs.common.settings")}
    </paper-tab>
    </paper-tabs>
    </app-header>

    ${this.panel,U`
    <hacs-panel
    .hass=${this.hass}
    .configuration=${this.configuration}
    .repositories=${this.repositories}
    .panel=${this.panel}
    .repository_view=${this.repository_view}
    .repository=${this.repository}
    >
    </hacs-panel>`}

    ${"settings"===this.panel?U`
    <hacs-panel-settings
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repositories=${this.repositories}>
        </hacs-panel-settings>`:""}

    </app-header-layout>`}handlePageSelected(t){this.repository_view=!1;const e=t.detail.item.getAttribute("page-name");this.panel=e,this.requestUpdate(),e!==this._page&&ut(0,`/hacs/${e}`),function(t,e){const i=e,s=Math.random(),o=Date.now(),r=i.scrollTop,n=0-r;t._currentAnimationId=s,function e(){const a=Date.now()-o;var p;a>200?i.scrollTop=0:t._currentAnimationId===s&&(i.scrollTop=(p=a,-n*(p/=200)*(p-2)+r),requestAnimationFrame(e.bind(t)))}.call(t)}(this,this.shadowRoot.querySelector("app-header-layout").header.scrollTarget)}get _page(){return null===this.route.path.substr(1)?"installed":this.route.path.substr(1)}static get styles(){return[yt]}};t([nt()],Ut.prototype,"hass",void 0),t([nt()],Ut.prototype,"repositories",void 0),t([nt()],Ut.prototype,"configuration",void 0),t([nt()],Ut.prototype,"route",void 0),t([nt()],Ut.prototype,"narrow",void 0),t([nt()],Ut.prototype,"panel",void 0),t([nt()],Ut.prototype,"repository",void 0),t([nt()],Ut.prototype,"repository_view",void 0),Ut=t([st("hacs-frontend")],Ut);
