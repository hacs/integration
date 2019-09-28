function t(t,e,r,i){var s,o=arguments.length,n=o<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,r):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,r,i);else for(var a=t.length-1;a>=0;a--)(s=t[a])&&(n=(o<3?s(n):o>3?s(e,r,n):s(e,r))||n);return o>3&&n&&Object.defineProperty(e,r,n),n}const e=new WeakMap,r=t=>"function"==typeof t&&e.has(t),i=void 0!==window.customElements&&void 0!==window.customElements.polyfillWrapFlushCallback,s=(t,e,r=null)=>{for(;e!==r;){const r=e.nextSibling;t.removeChild(e),e=r}},o={},n={},a=`{{lit-${String(Math.random()).slice(2)}}}`,p=`\x3c!--${a}--\x3e`,l=new RegExp(`${a}|${p}`),c="$lit$";class h{constructor(t,e){this.parts=[],this.element=e;const r=[],i=[],s=document.createTreeWalker(e.content,133,null,!1);let o=0,n=-1,p=0;const{strings:h,values:{length:u}}=t;for(;p<u;){const t=s.nextNode();if(null!==t){if(n++,1===t.nodeType){if(t.hasAttributes()){const e=t.attributes,{length:r}=e;let i=0;for(let t=0;t<r;t++)d(e[t].name,c)&&i++;for(;i-- >0;){const e=h[p],r=f.exec(e)[2],i=r.toLowerCase()+c,s=t.getAttribute(i);t.removeAttribute(i);const o=s.split(l);this.parts.push({type:"attribute",index:n,name:r,strings:o}),p+=o.length-1}}"TEMPLATE"===t.tagName&&(i.push(t),s.currentNode=t.content)}else if(3===t.nodeType){const e=t.data;if(e.indexOf(a)>=0){const i=t.parentNode,s=e.split(l),o=s.length-1;for(let e=0;e<o;e++){let r,o=s[e];if(""===o)r=m();else{const t=f.exec(o);null!==t&&d(t[2],c)&&(o=o.slice(0,t.index)+t[1]+t[2].slice(0,-c.length)+t[3]),r=document.createTextNode(o)}i.insertBefore(r,t),this.parts.push({type:"node",index:++n})}""===s[o]?(i.insertBefore(m(),t),r.push(t)):t.data=s[o],p+=o}}else if(8===t.nodeType)if(t.data===a){const e=t.parentNode;null!==t.previousSibling&&n!==o||(n++,e.insertBefore(m(),t)),o=n,this.parts.push({type:"node",index:n}),null===t.nextSibling?t.data="":(r.push(t),n--),p++}else{let e=-1;for(;-1!==(e=t.data.indexOf(a,e+1));)this.parts.push({type:"node",index:-1}),p++}}else s.currentNode=i.pop()}for(const t of r)t.parentNode.removeChild(t)}}const d=(t,e)=>{const r=t.length-e.length;return r>=0&&t.slice(r)===e},u=t=>-1!==t.index,m=()=>document.createComment(""),f=/([ \x09\x0a\x0c\x0d])([^\0-\x1F\x7F-\x9F "'>=\/]+)([ \x09\x0a\x0c\x0d]*=[ \x09\x0a\x0c\x0d]*(?:[^ \x09\x0a\x0c\x0d"'`<>=]*|"[^"]*|'[^']*))$/;class g{constructor(t,e,r){this.__parts=[],this.template=t,this.processor=e,this.options=r}update(t){let e=0;for(const r of this.__parts)void 0!==r&&r.setValue(t[e]),e++;for(const t of this.__parts)void 0!==t&&t.commit()}_clone(){const t=i?this.template.element.content.cloneNode(!0):document.importNode(this.template.element.content,!0),e=[],r=this.template.parts,s=document.createTreeWalker(t,133,null,!1);let o,n=0,a=0,p=s.nextNode();for(;n<r.length;)if(o=r[n],u(o)){for(;a<o.index;)a++,"TEMPLATE"===p.nodeName&&(e.push(p),s.currentNode=p.content),null===(p=s.nextNode())&&(s.currentNode=e.pop(),p=s.nextNode());if("node"===o.type){const t=this.processor.handleTextExpression(this.options);t.insertAfterNode(p.previousSibling),this.__parts.push(t)}else this.__parts.push(...this.processor.handleAttributeExpressions(p,o.name,o.strings,this.options));n++}else this.__parts.push(void 0),n++;return i&&(document.adoptNode(t),customElements.upgrade(t)),t}}const y=` ${a} `;class _{constructor(t,e,r,i){this.strings=t,this.values=e,this.type=r,this.processor=i}getHTML(){const t=this.strings.length-1;let e="",r=!1;for(let i=0;i<t;i++){const t=this.strings[i],s=t.lastIndexOf("\x3c!--");r=(s>-1||r)&&-1===t.indexOf("--\x3e",s+1);const o=f.exec(t);e+=null===o?t+(r?y:p):t.substr(0,o.index)+o[1]+o[2]+c+o[3]+a}return e+=this.strings[t]}getTemplateElement(){const t=document.createElement("template");return t.innerHTML=this.getHTML(),t}}const v=t=>null===t||!("object"==typeof t||"function"==typeof t),w=t=>Array.isArray(t)||!(!t||!t[Symbol.iterator]);class b{constructor(t,e,r){this.dirty=!0,this.element=t,this.name=e,this.strings=r,this.parts=[];for(let t=0;t<r.length-1;t++)this.parts[t]=this._createPart()}_createPart(){return new S(this)}_getValue(){const t=this.strings,e=t.length-1;let r="";for(let i=0;i<e;i++){r+=t[i];const e=this.parts[i];if(void 0!==e){const t=e.value;if(v(t)||!w(t))r+="string"==typeof t?t:String(t);else for(const e of t)r+="string"==typeof e?e:String(e)}}return r+=t[e]}commit(){this.dirty&&(this.dirty=!1,this.element.setAttribute(this.name,this._getValue()))}}class S{constructor(t){this.value=void 0,this.committer=t}setValue(t){t===o||v(t)&&t===this.value||(this.value=t,r(t)||(this.committer.dirty=!0))}commit(){for(;r(this.value);){const t=this.value;this.value=o,t(this)}this.value!==o&&this.committer.commit()}}class x{constructor(t){this.value=void 0,this.__pendingValue=void 0,this.options=t}appendInto(t){this.startNode=t.appendChild(m()),this.endNode=t.appendChild(m())}insertAfterNode(t){this.startNode=t,this.endNode=t.nextSibling}appendIntoPart(t){t.__insert(this.startNode=m()),t.__insert(this.endNode=m())}insertAfterPart(t){t.__insert(this.startNode=m()),this.endNode=t.endNode,t.endNode=this.startNode}setValue(t){this.__pendingValue=t}commit(){for(;r(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=o,t(this)}const t=this.__pendingValue;t!==o&&(v(t)?t!==this.value&&this.__commitText(t):t instanceof _?this.__commitTemplateResult(t):t instanceof Node?this.__commitNode(t):w(t)?this.__commitIterable(t):t===n?(this.value=n,this.clear()):this.__commitText(t))}__insert(t){this.endNode.parentNode.insertBefore(t,this.endNode)}__commitNode(t){this.value!==t&&(this.clear(),this.__insert(t),this.value=t)}__commitText(t){const e=this.startNode.nextSibling,r="string"==typeof(t=null==t?"":t)?t:String(t);e===this.endNode.previousSibling&&3===e.nodeType?e.data=r:this.__commitNode(document.createTextNode(r)),this.value=t}__commitTemplateResult(t){const e=this.options.templateFactory(t);if(this.value instanceof g&&this.value.template===e)this.value.update(t.values);else{const r=new g(e,t.processor,this.options),i=r._clone();r.update(t.values),this.__commitNode(i),this.value=r}}__commitIterable(t){Array.isArray(this.value)||(this.value=[],this.clear());const e=this.value;let r,i=0;for(const s of t)void 0===(r=e[i])&&(r=new x(this.options),e.push(r),0===i?r.appendIntoPart(this):r.insertAfterPart(e[i-1])),r.setValue(s),r.commit(),i++;i<e.length&&(e.length=i,this.clear(r&&r.endNode))}clear(t=this.startNode){s(this.startNode.parentNode,t.nextSibling,this.endNode)}}class P{constructor(t,e,r){if(this.value=void 0,this.__pendingValue=void 0,2!==r.length||""!==r[0]||""!==r[1])throw new Error("Boolean attributes can only contain a single expression");this.element=t,this.name=e,this.strings=r}setValue(t){this.__pendingValue=t}commit(){for(;r(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=o,t(this)}if(this.__pendingValue===o)return;const t=!!this.__pendingValue;this.value!==t&&(t?this.element.setAttribute(this.name,""):this.element.removeAttribute(this.name),this.value=t),this.__pendingValue=o}}class C extends b{constructor(t,e,r){super(t,e,r),this.single=2===r.length&&""===r[0]&&""===r[1]}_createPart(){return new $(this)}_getValue(){return this.single?this.parts[0].value:super._getValue()}commit(){this.dirty&&(this.dirty=!1,this.element[this.name]=this._getValue())}}class $ extends S{}let k=!1;try{const t={get capture(){return k=!0,!1}};window.addEventListener("test",t,t),window.removeEventListener("test",t,t)}catch(t){}class N{constructor(t,e,r){this.value=void 0,this.__pendingValue=void 0,this.element=t,this.eventName=e,this.eventContext=r,this.__boundHandleEvent=(t=>this.handleEvent(t))}setValue(t){this.__pendingValue=t}commit(){for(;r(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=o,t(this)}if(this.__pendingValue===o)return;const t=this.__pendingValue,e=this.value,i=null==t||null!=e&&(t.capture!==e.capture||t.once!==e.once||t.passive!==e.passive),s=null!=t&&(null==e||i);i&&this.element.removeEventListener(this.eventName,this.__boundHandleEvent,this.__options),s&&(this.__options=E(t),this.element.addEventListener(this.eventName,this.__boundHandleEvent,this.__options)),this.value=t,this.__pendingValue=o}handleEvent(t){"function"==typeof this.value?this.value.call(this.eventContext||this.element,t):this.value.handleEvent(t)}}const E=t=>t&&(k?{capture:t.capture,passive:t.passive,once:t.once}:t.capture);const A=new class{handleAttributeExpressions(t,e,r,i){const s=e[0];return"."===s?new C(t,e.slice(1),r).parts:"@"===s?[new N(t,e.slice(1),i.eventContext)]:"?"===s?[new P(t,e.slice(1),r)]:new b(t,e,r).parts}handleTextExpression(t){return new x(t)}};function T(t){let e=z.get(t.type);void 0===e&&(e={stringsArray:new WeakMap,keyString:new Map},z.set(t.type,e));let r=e.stringsArray.get(t.strings);if(void 0!==r)return r;const i=t.strings.join(a);return void 0===(r=e.keyString.get(i))&&(r=new h(t,t.getTemplateElement()),e.keyString.set(i,r)),e.stringsArray.set(t.strings,r),r}const z=new Map,U=new WeakMap;(window.litHtmlVersions||(window.litHtmlVersions=[])).push("1.1.2");const R=(t,...e)=>new _(t,e,"html",A),O=133;function V(t,e){const{element:{content:r},parts:i}=t,s=document.createTreeWalker(r,O,null,!1);let o=q(i),n=i[o],a=-1,p=0;const l=[];let c=null;for(;s.nextNode();){a++;const t=s.currentNode;for(t.previousSibling===c&&(c=null),e.has(t)&&(l.push(t),null===c&&(c=t)),null!==c&&p++;void 0!==n&&n.index===a;)n.index=null!==c?-1:n.index-p,n=i[o=q(i,o)]}l.forEach(t=>t.parentNode.removeChild(t))}const M=t=>{let e=11===t.nodeType?0:1;const r=document.createTreeWalker(t,O,null,!1);for(;r.nextNode();)e++;return e},q=(t,e=-1)=>{for(let r=e+1;r<t.length;r++){const e=t[r];if(u(e))return r}return-1};const j=(t,e)=>`${t}--${e}`;let I=!0;void 0===window.ShadyCSS?I=!1:void 0===window.ShadyCSS.prepareTemplateDom&&(console.warn("Incompatible ShadyCSS version detected. Please update to at least @webcomponents/webcomponentsjs@2.0.2 and @webcomponents/shadycss@1.3.1."),I=!1);const H=t=>e=>{const r=j(e.type,t);let i=z.get(r);void 0===i&&(i={stringsArray:new WeakMap,keyString:new Map},z.set(r,i));let s=i.stringsArray.get(e.strings);if(void 0!==s)return s;const o=e.strings.join(a);if(void 0===(s=i.keyString.get(o))){const r=e.getTemplateElement();I&&window.ShadyCSS.prepareTemplateDom(r,t),s=new h(e,r),i.keyString.set(o,s)}return i.stringsArray.set(e.strings,s),s},F=["html","svg"],L=new Set,B=(t,e,r)=>{L.add(t);const i=r?r.element:document.createElement("template"),s=e.querySelectorAll("style"),{length:o}=s;if(0===o)return void window.ShadyCSS.prepareTemplateStyles(i,t);const n=document.createElement("style");for(let t=0;t<o;t++){const e=s[t];e.parentNode.removeChild(e),n.textContent+=e.textContent}(t=>{F.forEach(e=>{const r=z.get(j(e,t));void 0!==r&&r.keyString.forEach(t=>{const{element:{content:e}}=t,r=new Set;Array.from(e.querySelectorAll("style")).forEach(t=>{r.add(t)}),V(t,r)})})})(t);const a=i.content;r?function(t,e,r=null){const{element:{content:i},parts:s}=t;if(null==r)return void i.appendChild(e);const o=document.createTreeWalker(i,O,null,!1);let n=q(s),a=0,p=-1;for(;o.nextNode();)for(p++,o.currentNode===r&&(a=M(e),r.parentNode.insertBefore(e,r));-1!==n&&s[n].index===p;){if(a>0){for(;-1!==n;)s[n].index+=a,n=q(s,n);return}n=q(s,n)}}(r,n,a.firstChild):a.insertBefore(n,a.firstChild),window.ShadyCSS.prepareTemplateStyles(i,t);const p=a.querySelector("style");if(window.ShadyCSS.nativeShadow&&null!==p)e.insertBefore(p.cloneNode(!0),e.firstChild);else if(r){a.insertBefore(n,a.firstChild);const t=new Set;t.add(n),V(r,t)}},W=(t,e,r)=>{if(!r||"object"!=typeof r||!r.scopeName)throw new Error("The `scopeName` option is required.");const i=r.scopeName,o=U.has(e),n=I&&11===e.nodeType&&!!e.host,a=n&&!L.has(i),p=a?document.createDocumentFragment():e;if(((t,e,r)=>{let i=U.get(e);void 0===i&&(s(e,e.firstChild),U.set(e,i=new x(Object.assign({templateFactory:T},r))),i.appendInto(e)),i.setValue(t),i.commit()})(t,p,Object.assign({templateFactory:H(i)},r)),a){const t=U.get(p);U.delete(p);const r=t.value instanceof g?t.value.template:void 0;B(i,p,r),s(e,e.firstChild),e.appendChild(p),U.set(e,t)}!o&&n&&window.ShadyCSS.styleElement(e.host)};window.JSCompiler_renameProperty=((t,e)=>t);const D={toAttribute(t,e){switch(e){case Boolean:return t?"":null;case Object:case Array:return null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){switch(e){case Boolean:return null!==t;case Number:return null===t?null:Number(t);case Object:case Array:return JSON.parse(t)}return t}},J=(t,e)=>e!==t&&(e==e||t==t),Z={attribute:!0,type:String,converter:D,reflect:!1,hasChanged:J},Q=Promise.resolve(!0),G=1,K=4,X=8,Y=16,tt=32,et="finalized";class rt extends HTMLElement{constructor(){super(),this._updateState=0,this._instanceProperties=void 0,this._updatePromise=Q,this._hasConnectedResolver=void 0,this._changedProperties=new Map,this._reflectingProperties=void 0,this.initialize()}static get observedAttributes(){this.finalize();const t=[];return this._classProperties.forEach((e,r)=>{const i=this._attributeNameForProperty(r,e);void 0!==i&&(this._attributeToPropertyMap.set(i,r),t.push(i))}),t}static _ensureClassProperties(){if(!this.hasOwnProperty(JSCompiler_renameProperty("_classProperties",this))){this._classProperties=new Map;const t=Object.getPrototypeOf(this)._classProperties;void 0!==t&&t.forEach((t,e)=>this._classProperties.set(e,t))}}static createProperty(t,e=Z){if(this._ensureClassProperties(),this._classProperties.set(t,e),e.noAccessor||this.prototype.hasOwnProperty(t))return;const r="symbol"==typeof t?Symbol():`__${t}`;Object.defineProperty(this.prototype,t,{get(){return this[r]},set(e){const i=this[t];this[r]=e,this._requestUpdate(t,i)},configurable:!0,enumerable:!0})}static finalize(){const t=Object.getPrototypeOf(this);if(t.hasOwnProperty(et)||t.finalize(),this[et]=!0,this._ensureClassProperties(),this._attributeToPropertyMap=new Map,this.hasOwnProperty(JSCompiler_renameProperty("properties",this))){const t=this.properties,e=[...Object.getOwnPropertyNames(t),..."function"==typeof Object.getOwnPropertySymbols?Object.getOwnPropertySymbols(t):[]];for(const r of e)this.createProperty(r,t[r])}}static _attributeNameForProperty(t,e){const r=e.attribute;return!1===r?void 0:"string"==typeof r?r:"string"==typeof t?t.toLowerCase():void 0}static _valueHasChanged(t,e,r=J){return r(t,e)}static _propertyValueFromAttribute(t,e){const r=e.type,i=e.converter||D,s="function"==typeof i?i:i.fromAttribute;return s?s(t,r):t}static _propertyValueToAttribute(t,e){if(void 0===e.reflect)return;const r=e.type,i=e.converter;return(i&&i.toAttribute||D.toAttribute)(t,r)}initialize(){this._saveInstanceProperties(),this._requestUpdate()}_saveInstanceProperties(){this.constructor._classProperties.forEach((t,e)=>{if(this.hasOwnProperty(e)){const t=this[e];delete this[e],this._instanceProperties||(this._instanceProperties=new Map),this._instanceProperties.set(e,t)}})}_applyInstanceProperties(){this._instanceProperties.forEach((t,e)=>this[e]=t),this._instanceProperties=void 0}connectedCallback(){this._updateState=this._updateState|tt,this._hasConnectedResolver&&(this._hasConnectedResolver(),this._hasConnectedResolver=void 0)}disconnectedCallback(){}attributeChangedCallback(t,e,r){e!==r&&this._attributeToProperty(t,r)}_propertyToAttribute(t,e,r=Z){const i=this.constructor,s=i._attributeNameForProperty(t,r);if(void 0!==s){const t=i._propertyValueToAttribute(e,r);if(void 0===t)return;this._updateState=this._updateState|X,null==t?this.removeAttribute(s):this.setAttribute(s,t),this._updateState=this._updateState&~X}}_attributeToProperty(t,e){if(this._updateState&X)return;const r=this.constructor,i=r._attributeToPropertyMap.get(t);if(void 0!==i){const t=r._classProperties.get(i)||Z;this._updateState=this._updateState|Y,this[i]=r._propertyValueFromAttribute(e,t),this._updateState=this._updateState&~Y}}_requestUpdate(t,e){let r=!0;if(void 0!==t){const i=this.constructor,s=i._classProperties.get(t)||Z;i._valueHasChanged(this[t],e,s.hasChanged)?(this._changedProperties.has(t)||this._changedProperties.set(t,e),!0!==s.reflect||this._updateState&Y||(void 0===this._reflectingProperties&&(this._reflectingProperties=new Map),this._reflectingProperties.set(t,s))):r=!1}!this._hasRequestedUpdate&&r&&this._enqueueUpdate()}requestUpdate(t,e){return this._requestUpdate(t,e),this.updateComplete}async _enqueueUpdate(){let t,e;this._updateState=this._updateState|K;const r=this._updatePromise;this._updatePromise=new Promise((r,i)=>{t=r,e=i});try{await r}catch(t){}this._hasConnected||await new Promise(t=>this._hasConnectedResolver=t);try{const t=this.performUpdate();null!=t&&await t}catch(t){e(t)}t(!this._hasRequestedUpdate)}get _hasConnected(){return this._updateState&tt}get _hasRequestedUpdate(){return this._updateState&K}get hasUpdated(){return this._updateState&G}performUpdate(){this._instanceProperties&&this._applyInstanceProperties();let t=!1;const e=this._changedProperties;try{(t=this.shouldUpdate(e))&&this.update(e)}catch(e){throw t=!1,e}finally{this._markUpdated()}t&&(this._updateState&G||(this._updateState=this._updateState|G,this.firstUpdated(e)),this.updated(e))}_markUpdated(){this._changedProperties=new Map,this._updateState=this._updateState&~K}get updateComplete(){return this._getUpdateComplete()}_getUpdateComplete(){return this._updatePromise}shouldUpdate(t){return!0}update(t){void 0!==this._reflectingProperties&&this._reflectingProperties.size>0&&(this._reflectingProperties.forEach((t,e)=>this._propertyToAttribute(e,this[e],t)),this._reflectingProperties=void 0)}updated(t){}firstUpdated(t){}}rt[et]=!0;const it=t=>e=>"function"==typeof e?((t,e)=>(window.customElements.define(t,e),e))(t,e):((t,e)=>{const{kind:r,elements:i}=e;return{kind:r,elements:i,finisher(e){window.customElements.define(t,e)}}})(t,e),st=(t,e)=>"method"!==e.kind||!e.descriptor||"value"in e.descriptor?{kind:"field",key:Symbol(),placement:"own",descriptor:{},initializer(){"function"==typeof e.initializer&&(this[e.key]=e.initializer.call(this))},finisher(r){r.createProperty(e.key,t)}}:Object.assign({},e,{finisher(r){r.createProperty(e.key,t)}}),ot=(t,e,r)=>{e.constructor.createProperty(r,t)};function nt(t){return(e,r)=>void 0!==r?ot(t,e,r):st(t,e)}const at="adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,pt=Symbol();class lt{constructor(t,e){if(e!==pt)throw new Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t}get styleSheet(){return void 0===this._styleSheet&&(at?(this._styleSheet=new CSSStyleSheet,this._styleSheet.replaceSync(this.cssText)):this._styleSheet=null),this._styleSheet}toString(){return this.cssText}}const ct=(t,...e)=>{const r=e.reduce((e,r,i)=>e+(t=>{if(t instanceof lt)return t.cssText;if("number"==typeof t)return t;throw new Error(`Value passed to 'css' function must be a 'css' function result: ${t}. Use 'unsafeCSS' to pass non-literal values, but\n            take care to ensure page security.`)})(r)+t[i+1],t[0]);return new lt(r,pt)};(window.litElementVersions||(window.litElementVersions=[])).push("2.2.1");const ht=t=>t.flat?t.flat(1/0):function t(e,r=[]){for(let i=0,s=e.length;i<s;i++){const s=e[i];Array.isArray(s)?t(s,r):r.push(s)}return r}(t);class dt extends rt{static finalize(){super.finalize.call(this),this._styles=this.hasOwnProperty(JSCompiler_renameProperty("styles",this))?this._getUniqueStyles():this._styles||[]}static _getUniqueStyles(){const t=this.styles,e=[];if(Array.isArray(t)){ht(t).reduceRight((t,e)=>(t.add(e),t),new Set).forEach(t=>e.unshift(t))}else t&&e.push(t);return e}initialize(){super.initialize(),this.renderRoot=this.createRenderRoot(),window.ShadowRoot&&this.renderRoot instanceof window.ShadowRoot&&this.adoptStyles()}createRenderRoot(){return this.attachShadow({mode:"open"})}adoptStyles(){const t=this.constructor._styles;0!==t.length&&(void 0===window.ShadyCSS||window.ShadyCSS.nativeShadow?at?this.renderRoot.adoptedStyleSheets=t.map(t=>t.styleSheet):this._needsShimAdoptedStyleSheets=!0:window.ShadyCSS.ScopingShim.prepareAdoptedCssText(t.map(t=>t.cssText),this.localName))}connectedCallback(){super.connectedCallback(),this.hasUpdated&&void 0!==window.ShadyCSS&&window.ShadyCSS.styleElement(this)}update(t){super.update(t);const e=this.render();e instanceof _&&this.constructor.render(e,this.renderRoot,{scopeName:this.localName,eventContext:this}),this._needsShimAdoptedStyleSheets&&(this._needsShimAdoptedStyleSheets=!1,this.constructor._styles.forEach(t=>{const e=document.createElement("style");e.textContent=t.cssText,this.renderRoot.appendChild(e)}))}render(){}}dt.finalized=!0,dt.render=W;const ut=(t,e,r=!0)=>{r?history.replaceState(null,"",e):history.pushState(null,"",e)},mt=t=>null!==t,ft=t=>t?"":null,gt=(t,e)=>e!==t&&(e==e||t==t),yt={attribute:!0,type:String,reflect:!1,hasChanged:gt},_t=new Promise(t=>t(!0)),vt=1,wt=4,bt=8;class St extends HTMLElement{constructor(){super(),this._updateState=0,this._instanceProperties=void 0,this._updatePromise=_t,this._changedProperties=new Map,this._reflectingProperties=void 0,this.initialize()}static get observedAttributes(){this._finalize();const t=[];for(const[e,r]of this._classProperties){const i=this._attributeNameForProperty(e,r);void 0!==i&&(this._attributeToPropertyMap.set(i,e),t.push(i))}return t}static createProperty(t,e=yt){if(!this.hasOwnProperty("_classProperties")){this._classProperties=new Map;const t=Object.getPrototypeOf(this)._classProperties;void 0!==t&&t.forEach((t,e)=>this._classProperties.set(e,t))}if(this._classProperties.set(t,e),this.prototype.hasOwnProperty(t))return;const r="symbol"==typeof t?Symbol():`__${t}`;Object.defineProperty(this.prototype,t,{get(){return this[r]},set(i){const s=this[t];this[r]=i,this._requestPropertyUpdate(t,s,e)},configurable:!0,enumerable:!0})}static _finalize(){if(this.hasOwnProperty("_finalized")&&this._finalized)return;const t=Object.getPrototypeOf(this);"function"==typeof t._finalize&&t._finalize(),this._finalized=!0,this._attributeToPropertyMap=new Map;const e=this.properties,r=[...Object.getOwnPropertyNames(e),..."function"==typeof Object.getOwnPropertySymbols?Object.getOwnPropertySymbols(e):[]];for(const t of r)this.createProperty(t,e[t])}static _attributeNameForProperty(t,e){const r=void 0!==e&&e.attribute;return!1===r?void 0:"string"==typeof r?r:"string"==typeof t?t.toLowerCase():void 0}static _valueHasChanged(t,e,r=gt){return r(t,e)}static _propertyValueFromAttribute(t,e){const r=e&&e.type;if(void 0===r)return t;const i=r===Boolean?mt:"function"==typeof r?r:r.fromAttribute;return i?i(t):t}static _propertyValueToAttribute(t,e){if(void 0===e||void 0===e.reflect)return;return(e.type===Boolean?ft:e.type&&e.type.toAttribute||String)(t)}initialize(){this.renderRoot=this.createRenderRoot(),this._saveInstanceProperties()}_saveInstanceProperties(){for(const[t]of this.constructor._classProperties)if(this.hasOwnProperty(t)){const e=this[t];delete this[t],this._instanceProperties||(this._instanceProperties=new Map),this._instanceProperties.set(t,e)}}_applyInstanceProperties(){for(const[t,e]of this._instanceProperties)this[t]=e;this._instanceProperties=void 0}createRenderRoot(){return this.attachShadow({mode:"open"})}connectedCallback(){this._updateState&vt?void 0!==window.ShadyCSS&&window.ShadyCSS.styleElement(this):this.requestUpdate()}disconnectedCallback(){}attributeChangedCallback(t,e,r){e!==r&&this._attributeToProperty(t,r)}_propertyToAttribute(t,e,r=yt){const i=this.constructor,s=i._propertyValueToAttribute(e,r);if(void 0!==s){const e=i._attributeNameForProperty(t,r);void 0!==e&&(this._updateState=this._updateState|bt,null===s?this.removeAttribute(e):this.setAttribute(e,s),this._updateState=this._updateState&~bt)}}_attributeToProperty(t,e){if(!(this._updateState&bt)){const r=this.constructor,i=r._attributeToPropertyMap.get(t);if(void 0!==i){const t=r._classProperties.get(i);this[i]=r._propertyValueFromAttribute(e,t)}}}requestUpdate(t,e){if(void 0!==t){const r=this.constructor._classProperties.get(t)||yt;return this._requestPropertyUpdate(t,e,r)}return this._invalidate()}_requestPropertyUpdate(t,e,r){return this.constructor._valueHasChanged(this[t],e,r.hasChanged)?(this._changedProperties.has(t)||this._changedProperties.set(t,e),!0===r.reflect&&(void 0===this._reflectingProperties&&(this._reflectingProperties=new Map),this._reflectingProperties.set(t,r)),this._invalidate()):this.updateComplete}async _invalidate(){if(!this._hasRequestedUpdate){let t;this._updateState=this._updateState|wt;const e=this._updatePromise;this._updatePromise=new Promise(e=>t=e),await e,this._validate(),t(!this._hasRequestedUpdate)}return this.updateComplete}get _hasRequestedUpdate(){return this._updateState&wt}_validate(){if(this._instanceProperties&&this._applyInstanceProperties(),this.shouldUpdate(this._changedProperties)){const t=this._changedProperties;this.update(t),this._markUpdated(),this._updateState&vt||(this._updateState=this._updateState|vt,this.firstUpdated(t)),this.updated(t)}else this._markUpdated()}_markUpdated(){this._changedProperties=new Map,this._updateState=this._updateState&~wt}get updateComplete(){return this._updatePromise}shouldUpdate(t){return!0}update(t){if(void 0!==this._reflectingProperties&&this._reflectingProperties.size>0){for(const[t,e]of this._reflectingProperties)this._propertyToAttribute(t,this[t],e);this._reflectingProperties=void 0}}updated(t){}firstUpdated(t){}}St._attributeToPropertyMap=new Map,St._finalized=!0,St._classProperties=new Map,St.properties={};class xt extends St{update(t){super.update(t);const e=this.render();e instanceof _&&this.constructor.render(e,this.renderRoot,{scopeName:this.localName,eventContext:this})}render(){}}xt.render=W;window.customElements.define("granite-spinner",class extends xt{static get properties(){return{active:{type:Boolean,reflect:!0},hover:{type:Boolean,reflect:!0},size:{type:Number},color:{type:String},lineWidth:{type:String},containerHeight:{type:Number,value:150},debug:{type:Boolean}}}constructor(){super(),this.size=100,this.color="#28b6d8",this.lineWidth="1.5em",this.containerHeight=150}firstUpdated(){this.debug&&console.log("[granite-spinner] firstUpdated")}shouldUpdate(){return this.debug&&console.log("[granite-spinner] shouldUpdate",this.lineWidth),!0}render(){if(this.active)return R`
      ${this._renderStyles()}      
      <div id="spinner-container">
        <div id="spinner" class="loading">
        </div>
      </div>
    `}_renderStyles(){return R`
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
      
    `}});let Pt=class extends dt{render(){return R`
            <granite-spinner color="var(--primary-color)" active hover size=400 containerHeight=100%></granite-spinner>
            `}};function Ct(t){return t?JSON.parse('{"'+t.substring(1).replace(/&/g,'","').replace(/=/g,'":"')+'"}'):{}}function $t(t,e){if(function(t){return t?new RegExp("^(|/)"+t.replace(/:[^\s\/]+/g,"([\\wÀ-ÖØ-öø-ÿ-]+)")+"(|/)$"):new RegExp("(^$|^/$)")}(e).test(t))return!0}Pt=t([it("hacs-spinner")],Pt);let kt=t=>(class extends t{static get properties(){return{route:{type:String,reflect:!0,attribute:"route"},canceled:{type:Boolean}}}firstUpdated(){this.router(this.constructor.routes,(...t)=>this.onRoute(...t)),window.addEventListener("route",()=>{this.router(this.constructor.routes,(...t)=>this.onRoute(...t))}),window.onpopstate=(()=>{window.dispatchEvent(new CustomEvent("route"))}),super.firstUpdated&&super.firstUpdated()}router(t,e){this.canceled=!0;const r=decodeURI(window.location.pathname),i=decodeURI(window.location.search);let s=t.filter(t=>"*"===t.pattern)[0];if((t=t.filter(t=>"*"!==t.pattern&&$t(r,t.pattern))).length){let s=t[0];s.params=function(t,e){let r={};const i=t.split("/").filter(t=>""!=t),s=e.split("/").filter(t=>""!=t);return i.map((t,e)=>{/^:/.test(t)&&(r[t.substring(1)]=s[e])}),r}(s.pattern,r),s.query=Ct(i),s.guard&&"function"==typeof s.guard?(this.canceled=!1,Promise.resolve(s.guard()).then(t=>{this.canceled||(t?(s.callback&&s.callback(s.name,s.params,s.query,s.data),e(s.name,s.params,s.query,s.data)):(s.callback&&s.callback("not-authorized",s.params,s.query,s.data),e("not-authorized",s.params,s.query,s.data)))})):(s.callback&&s.callback(s.name,s.params,s.query,s.data),e(s.name,s.params,s.query,s.data))}else s?(s.callback&&s.callback(s.name,{},Ct(i),s.data),e(s.name,{},Ct(i),s.data)):e("not-found",{},Ct(i),s.data);super.router&&super.router()}});customElements.define("router-link",class extends dt{constructor(){super(),this.addEventListener("click",this.clickHandler.bind(this))}clickHandler(t){t.preventDefault(),window.history.pushState({},null,t.target.href+window.location.search),window.dispatchEvent(new CustomEvent("route"))}static get properties(){return{href:{type:String}}}render(){return R`
            <style>
                ::slotted(*) {
                    pointer-events: none;
                }
                a {
                    all: unset;
                    display: contents;
                    
                    /*Fallback for Edge*/
                    text-decoration: unset;
                    color: unset;
                }
            </style>
            <a href='${this.href}'>
                <slot></slot>
            </a>
        `}});customElements.define("router-slot",class extends dt{static get properties(){return{route:{type:String,reflect:!0,attribute:"route"}}}updated(t){t.has("route")&&this.slott()}slott(){this.route.length&&([...this.shadowRoot.querySelectorAll("[slot]")].map(t=>{this.appendChild(t)}),[...this.querySelectorAll(`[slot~=${this.route}]`)].map(t=>{this.shadowRoot.appendChild(t)}))}});let Nt=class extends dt{render(){var t=this.repositories.content||[];return t=this.repositories.content.filter(function(t){return t.installed}),R`
    <div class="hacs-repositories">
    ${t.map(t=>R`<ha-card header="${t.name}">
      <div class="card-content">
        <i>${t.description}<i>
      </div>
      </ha-card>
      `)}
    </div>
          `}static get styles(){return ct`
      :host {
        color: var(--primary-text-color);
      }
      ha-card {
        margin: 8px;
      }
      `}};t([nt()],Nt.prototype,"hass",void 0),t([nt()],Nt.prototype,"repositories",void 0),t([nt()],Nt.prototype,"configuration",void 0),Nt=t([it("hacs-panel-installed")],Nt);let Et=class extends dt{constructor(){super(...arguments),this.repository_view=!1}render(){if(/repository\//i.test(this.panel))return this.repository_view=!0,this.repository=this.panel.split("/")[1],R`
      <hacs-panel-repository
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .repository=${this.repository}>
      </hacs-panel-repository>`;{const e=this.panel,r=this.configuration;var t=this.repositories.content||[];return t=this.repositories.content.filter(function(t){if("installed"!==e){if("172733314"===t.id)return!1;if(t.hide)return!1;if(null!==r.country&&r.country!==t.country)return!1}return t.category===e}),R`
    <div class="card-group">
    ${t.sort((t,e)=>t.name>e.name?1:-1).map(t=>R`

      <paper-card @click="${this.getQuote}" .RepoID="${t.id}">
      <div class="card-content">
        <div>
          <ha-icon icon="mdi:cube" class="repo-state-${t.installed}" title="Add-on is running"></ha-icon>
          <div>
            <div class="title">${t.name}</div>
            <div class="addition">${t.description}</div>
          </div>
        </div>
      </div>
      </paper-card>

      `)}
    </div>
          `}}getQuote(t){var e=new CustomEvent("hacs-update",{detail:{stuff:"stuff"}});this.dispatchEvent(e),console.log(e),t.path.forEach(t=>{void 0!==t.RepoID&&(this.panel=`repository/${t.RepoID}`,this.repository=t.RepoID,this.repository_view=!0,ut(0,`/hacs/repository/${t.RepoID}`),this.requestUpdate())})}static get styles(){return ct`
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

    app-toolbar ha-menu-button + [main-title], app-toolbar ha-paper-icon-button-arrow-prev + [main-title], app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }

    h1 {
      font-family: var(--paper-font-title_-_font-family); -webkit-font-smoothing: var(--paper-font-title_-_-webkit-font-smoothing); white-space: var(--paper-font-title_-_white-space); overflow: var(--paper-font-title_-_overflow); text-overflow: var(--paper-font-title_-_text-overflow); font-size: var(--paper-font-title_-_font-size); font-weight: var(--paper-font-title_-_font-weight); line-height: var(--paper-font-title_-_line-height);
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

    .card-group {
      margin-top: 24px;
    }

    .card-group .title {
      color: var(--primary-text-color);
        font-size: 1.5em;
        padding-left: 8px;
        margin-bottom: 8px;
    }

    .card-group .description {
      font-size: 0.5em;
        font-weight: 500;
        margin-top: 4px;
    }

    .card-group paper-card {
      --card-group-columns: 4;
        width: calc(
          (100% - 12px * var(--card-group-columns)) / var(--card-group-columns)
        );
        margin: 4px;
        vertical-align: top;
        height: 144px;
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

    ha-call-api-button {
      font-weight: 500;
        color: var(--primary-color);
    }

    .error {
      color: var(--google-red-500);
        margin-top: 16px;
    }

    paper-card {
      cursor: pointer;
    }
    ha-icon {
      margin-right: 16px;
      float: left;
      color: var(--primary-text-color);
    }
    ha-icon.update {
      color: var(--paper-orange-400);
    }
    ha-icon.running,
    ha-icon.installed {
      color: var(--paper-green-400);
    }
    ha-icon.hassupdate,
    ha-icon.snapshot {
      color: var(--paper-item-icon-color);
    }
    ha-icon.not_available {
      color: var(--google-red-500);
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
      height: 2.4em;
      line-height: 1.2em;
    }
    ha-relative-time {
      display: block;
    }
    `}};t([nt()],Et.prototype,"hass",void 0),t([nt()],Et.prototype,"repositories",void 0),t([nt()],Et.prototype,"configuration",void 0),t([nt()],Et.prototype,"panel",void 0),t([nt()],Et.prototype,"repository_view",void 0),t([nt()],Et.prototype,"repository",void 0),Et=t([it("hacs-panel-store")],Et);let At=class extends dt{render(){return console.log("hass: ",this.hass),console.log("configuration: ",this.configuration),R`

    <ha-card header="${this.hass.localize("component.hacs.config.title")}">
      <div class="card content">



      </div>
    </ha-card>
          `}static get styles(){return ct`
      :host {
        color: var(--primary-text-color);
      }
      ha-card {
        margin: 8px;
      }
      `}};t([nt()],At.prototype,"hass",void 0),t([nt()],At.prototype,"repositories",void 0),t([nt()],At.prototype,"configuration",void 0),At=t([it("hacs-panel-settings")],At);let Tt=class extends dt{render(){var t=this.repository,e=(this.repositories.content,this.repositories.content.filter(function(e){return e.id===t})[0]);return R`

    <ha-card header="${e.name}">
      <div class="card content">
      </div>
    </ha-card>
          `}static get styles(){return ct`
      :host {
        color: var(--primary-text-color);
      }
      ha-card {
        margin: 8px;
      }
      `}};t([nt()],Tt.prototype,"hass",void 0),t([nt()],Tt.prototype,"repositories",void 0),t([nt()],Tt.prototype,"configuration",void 0),t([nt()],Tt.prototype,"repository",void 0),Tt=t([it("hacs-panel-repository")],Tt);class zt extends(kt(dt)){constructor(){super(...arguments),this.repository_view=!1}static get routes(){return[{name:"hacs-panel-settings",pattern:"hacs/settings"},{name:"hacs-panel-store",pattern:"hacs/integration"},{name:"hacs-panel-repository",pattern:"hacs/repository/:id"},{name:"hacs-panel-installed",pattern:"hacs/*"}]}render(){return/repository\//i.test(this.panel)?(this.repository_view=!0,this.repository=this.panel.split("/")[1]):this.repository_view=!1,R`
            ${this.repository_view?R`
            <hacs-panel-repository
            .hass=${this.hass}
            .configuration=${this.configuration}
            .repositories=${this.repositories}
            .repository=${this.repository}>
            </hacs-panel-repository>`:""}

            ${"installed"===this.panel?R`
            <hacs-panel-installed
                .hass=${this.hass}
                .configuration=${this.configuration}
                .repositories=${this.repositories}>
                </hacs-panel-installed>`:""}

            ${this.panel,R`
            <hacs-panel-store
            .hass=${this.hass}
            .configuration=${this.configuration}
            .repositories=${this.repositories}
            .panel=${this.panel}
            .repository_view=${this.repository_view}>
            </hacs-panel-store>`}

            ${"settings"===this.panel?R`
            <hacs-panel-settings
                .hass=${this.hass}
                .configuration=${this.configuration}
                .repositories=${this.repositories}>
                </hacs-panel-settings>`:""}
            `}onRoute(t,e,r,i){this.repository=e.id,console.log(t,e,r,i)}}t([nt()],zt.prototype,"hass",void 0),t([nt()],zt.prototype,"repositories",void 0),t([nt()],zt.prototype,"configuration",void 0),t([nt()],zt.prototype,"route",void 0),t([nt()],zt.prototype,"narrow",void 0),t([nt()],zt.prototype,"repository",void 0),t([nt()],zt.prototype,"panel",void 0),t([nt()],zt.prototype,"repository_view",void 0),customElements.define("hacs-router",zt);let Ut=class extends dt{constructor(){super(...arguments),this.repository_view=!1}getRepositories(){this.hass.connection.sendMessagePromise({type:"hacs/config"}).then(t=>{this.configuration=t},t=>{console.error("Message failed!",t)}),this.hass.connection.sendMessagePromise({type:"hacs/repositories"}).then(t=>{this.repositories=t},t=>{console.error("Message failed!",t)}),this.requestUpdate()}connectedCallback(){console.log("lit-parent setting up Registration Shop"),this.addEventListener("hacs-update",t=>{console.log(t),this.requestUpdate()}),super.connectedCallback()}firstUpdated(){this.panel=this._page,this.getRepositories(),/repository\//i.test(this.panel)?(this.repository_view=!0,this.repository=this.panel.split("/")[1]):this.repository_view=!1,this.addEventListener("hacs-update",async t=>{console.log(t),this.requestUpdate()}),function(){if(customElements.get("hui-view"))return!0;const t=document.createElement("partial-panel-resolver");t.hass=document.querySelector("home-assistant").hass,t.route={path:"/lovelace/"};try{document.querySelector("home-assistant").appendChild(t).catch(t=>{})}catch(e){document.querySelector("home-assistant").removeChild(t)}customElements.get("hui-view")}()}render(){return""===this.panel&&(ut(0,"/hacs/installed"),this.panel="installed"),console.log(this.panel),void 0===this.repositories?R`<hacs-spinner></hacs-spinner>`:(/repository\//i.test(this.panel)?(this.repository_view=!0,this.repository=this.panel.split("/")[1]):this.repository_view=!1,R`
    <app-header-layout has-scrolling-region>
    <app-header slot="header" fixed>
      <app-toolbar>
        <ha-menu-button .hass="${this.hass}" .narrow="${this.narrow}"></ha-menu-button>
        <div main-title>${this.hass.localize("component.hacs.config.title")}</div>
      </app-toolbar>
    <paper-tabs
    scrollable
    attr-for-selected="page-name"
    .selected="${this.panel}"
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

    ${this.configuration.appdaemon?R`<paper-tab page-name="appdaemon">
        ${this.hass.localize("component.hacs.common.appdaemon_apps")}
    </paper-tab>`:""}

    ${this.configuration.python_script?R`<paper-tab page-name="python_script">
        ${this.hass.localize("component.hacs.common.python_scripts")}
    </paper-tab>`:""}

    ${this.configuration.theme?R`<paper-tab page-name="theme">
        ${this.hass.localize("component.hacs.common.themes")}
    </paper-tab>`:""}

    <paper-tab class="right" page-name="settings">
    ${this.hass.localize("component.hacs.common.settings")}
    </paper-tab>
    </paper-tabs>
    </app-header>

    <hacs-router
    .hass=${this.hass}
    .configuration=${this.configuration}
    .repositories=${this.repositories}
    .repository=${this.repository}
    .panel=${this.panel}
    >
    </hacs-router>

    </app-header-layout>`)}handlePageSelected(t){this.repository_view=!1;const e=t.detail.item.getAttribute("page-name");this.panel=e,ut(0,`/hacs/${e}`),this.requestUpdate()}get _page(){return null===this.route.path.substr(1)?"installed":this.route.path.substr(1)}static get styles(){return ct`
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

    app-toolbar ha-menu-button + [main-title], app-toolbar ha-paper-icon-button-arrow-prev + [main-title], app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }

    h1 {
      font-family: var(--paper-font-title_-_font-family); -webkit-font-smoothing: var(--paper-font-title_-_-webkit-font-smoothing); white-space: var(--paper-font-title_-_white-space); overflow: var(--paper-font-title_-_overflow); text-overflow: var(--paper-font-title_-_text-overflow); font-size: var(--paper-font-title_-_font-size); font-weight: var(--paper-font-title_-_font-weight); line-height: var(--paper-font-title_-_line-height);
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

    .card-group {
      margin-top: 24px;
    }

    .card-group .title {
      color: var(--primary-text-color);
        font-size: 1.5em;
        padding-left: 8px;
        margin-bottom: 8px;
    }

    .card-group .description {
      font-size: 0.5em;
        font-weight: 500;
        margin-top: 4px;
    }

    .card-group paper-card {
      --card-group-columns: 4;
        width: calc(
          (100% - 12px * var(--card-group-columns)) / var(--card-group-columns)
        );
        margin: 4px;
        vertical-align: top;
        height: 144px;
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

    ha-call-api-button {
      font-weight: 500;
        color: var(--primary-color);
    }

    .error {
      color: var(--google-red-500);
        margin-top: 16px;
    }

    paper-card {
      cursor: pointer;
    }
    ha-icon {
      margin-right: 16px;
      float: left;
      color: var(--primary-text-color);
    }
    ha-icon.update {
      color: var(--paper-orange-400);
    }
    ha-icon.running,
    ha-icon.installed {
      color: var(--paper-green-400);
    }
    ha-icon.hassupdate,
    ha-icon.snapshot {
      color: var(--paper-item-icon-color);
    }
    ha-icon.not_available {
      color: var(--google-red-500);
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
      height: 2.4em;
      line-height: 1.2em;
    }
    ha-relative-time {
      display: block;
    }
    `}};t([nt()],Ut.prototype,"hass",void 0),t([nt()],Ut.prototype,"repositories",void 0),t([nt()],Ut.prototype,"configuration",void 0),t([nt()],Ut.prototype,"route",void 0),t([nt()],Ut.prototype,"narrow",void 0),t([nt()],Ut.prototype,"panel",void 0),t([nt()],Ut.prototype,"repository",void 0),t([nt()],Ut.prototype,"repository_view",void 0),Ut=t([it("hacs-frontend")],Ut);
