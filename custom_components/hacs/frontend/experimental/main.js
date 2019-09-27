function t(t,e,i,r){var s,o=arguments.length,n=o<3?e:null===r?r=Object.getOwnPropertyDescriptor(e,i):r;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,i,r);else for(var a=t.length-1;a>=0;a--)(s=t[a])&&(n=(o<3?s(n):o>3?s(e,i,n):s(e,i))||n);return o>3&&n&&Object.defineProperty(e,i,n),n}const e=new WeakMap,i=t=>"function"==typeof t&&e.has(t),r=void 0!==window.customElements&&void 0!==window.customElements.polyfillWrapFlushCallback,s=(t,e,i=null)=>{for(;e!==i;){const i=e.nextSibling;t.removeChild(e),e=i}},o={},n={},a=`{{lit-${String(Math.random()).slice(2)}}}`,p=`\x3c!--${a}--\x3e`,l=new RegExp(`${a}|${p}`),c="$lit$";class h{constructor(t,e){this.parts=[],this.element=e;const i=[],r=[],s=document.createTreeWalker(e.content,133,null,!1);let o=0,n=-1,p=0;const{strings:h,values:{length:u}}=t;for(;p<u;){const t=s.nextNode();if(null!==t){if(n++,1===t.nodeType){if(t.hasAttributes()){const e=t.attributes,{length:i}=e;let r=0;for(let t=0;t<i;t++)d(e[t].name,c)&&r++;for(;r-- >0;){const e=h[p],i=g.exec(e)[2],r=i.toLowerCase()+c,s=t.getAttribute(r);t.removeAttribute(r);const o=s.split(l);this.parts.push({type:"attribute",index:n,name:i,strings:o}),p+=o.length-1}}"TEMPLATE"===t.tagName&&(r.push(t),s.currentNode=t.content)}else if(3===t.nodeType){const e=t.data;if(e.indexOf(a)>=0){const r=t.parentNode,s=e.split(l),o=s.length-1;for(let e=0;e<o;e++){let i,o=s[e];if(""===o)i=m();else{const t=g.exec(o);null!==t&&d(t[2],c)&&(o=o.slice(0,t.index)+t[1]+t[2].slice(0,-c.length)+t[3]),i=document.createTextNode(o)}r.insertBefore(i,t),this.parts.push({type:"node",index:++n})}""===s[o]?(r.insertBefore(m(),t),i.push(t)):t.data=s[o],p+=o}}else if(8===t.nodeType)if(t.data===a){const e=t.parentNode;null!==t.previousSibling&&n!==o||(n++,e.insertBefore(m(),t)),o=n,this.parts.push({type:"node",index:n}),null===t.nextSibling?t.data="":(i.push(t),n--),p++}else{let e=-1;for(;-1!==(e=t.data.indexOf(a,e+1));)this.parts.push({type:"node",index:-1}),p++}}else s.currentNode=r.pop()}for(const t of i)t.parentNode.removeChild(t)}}const d=(t,e)=>{const i=t.length-e.length;return i>=0&&t.slice(i)===e},u=t=>-1!==t.index,m=()=>document.createComment(""),g=/([ \x09\x0a\x0c\x0d])([^\0-\x1F\x7F-\x9F "'>=\/]+)([ \x09\x0a\x0c\x0d]*=[ \x09\x0a\x0c\x0d]*(?:[^ \x09\x0a\x0c\x0d"'`<>=]*|"[^"]*|'[^']*))$/;class f{constructor(t,e,i){this.__parts=[],this.template=t,this.processor=e,this.options=i}update(t){let e=0;for(const i of this.__parts)void 0!==i&&i.setValue(t[e]),e++;for(const t of this.__parts)void 0!==t&&t.commit()}_clone(){const t=r?this.template.element.content.cloneNode(!0):document.importNode(this.template.element.content,!0),e=[],i=this.template.parts,s=document.createTreeWalker(t,133,null,!1);let o,n=0,a=0,p=s.nextNode();for(;n<i.length;)if(o=i[n],u(o)){for(;a<o.index;)a++,"TEMPLATE"===p.nodeName&&(e.push(p),s.currentNode=p.content),null===(p=s.nextNode())&&(s.currentNode=e.pop(),p=s.nextNode());if("node"===o.type){const t=this.processor.handleTextExpression(this.options);t.insertAfterNode(p.previousSibling),this.__parts.push(t)}else this.__parts.push(...this.processor.handleAttributeExpressions(p,o.name,o.strings,this.options));n++}else this.__parts.push(void 0),n++;return r&&(document.adoptNode(t),customElements.upgrade(t)),t}}const _=` ${a} `;class y{constructor(t,e,i,r){this.strings=t,this.values=e,this.type=i,this.processor=r}getHTML(){const t=this.strings.length-1;let e="",i=!1;for(let r=0;r<t;r++){const t=this.strings[r],s=t.lastIndexOf("\x3c!--");i=(s>-1||i)&&-1===t.indexOf("--\x3e",s+1);const o=g.exec(t);e+=null===o?t+(i?_:p):t.substr(0,o.index)+o[1]+o[2]+c+o[3]+a}return e+=this.strings[t]}getTemplateElement(){const t=document.createElement("template");return t.innerHTML=this.getHTML(),t}}const v=t=>null===t||!("object"==typeof t||"function"==typeof t),w=t=>Array.isArray(t)||!(!t||!t[Symbol.iterator]);class b{constructor(t,e,i){this.dirty=!0,this.element=t,this.name=e,this.strings=i,this.parts=[];for(let t=0;t<i.length-1;t++)this.parts[t]=this._createPart()}_createPart(){return new S(this)}_getValue(){const t=this.strings,e=t.length-1;let i="";for(let r=0;r<e;r++){i+=t[r];const e=this.parts[r];if(void 0!==e){const t=e.value;if(v(t)||!w(t))i+="string"==typeof t?t:String(t);else for(const e of t)i+="string"==typeof e?e:String(e)}}return i+=t[e]}commit(){this.dirty&&(this.dirty=!1,this.element.setAttribute(this.name,this._getValue()))}}class S{constructor(t){this.value=void 0,this.committer=t}setValue(t){t===o||v(t)&&t===this.value||(this.value=t,i(t)||(this.committer.dirty=!0))}commit(){for(;i(this.value);){const t=this.value;this.value=o,t(this)}this.value!==o&&this.committer.commit()}}class x{constructor(t){this.value=void 0,this.__pendingValue=void 0,this.options=t}appendInto(t){this.startNode=t.appendChild(m()),this.endNode=t.appendChild(m())}insertAfterNode(t){this.startNode=t,this.endNode=t.nextSibling}appendIntoPart(t){t.__insert(this.startNode=m()),t.__insert(this.endNode=m())}insertAfterPart(t){t.__insert(this.startNode=m()),this.endNode=t.endNode,t.endNode=this.startNode}setValue(t){this.__pendingValue=t}commit(){for(;i(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=o,t(this)}const t=this.__pendingValue;t!==o&&(v(t)?t!==this.value&&this.__commitText(t):t instanceof y?this.__commitTemplateResult(t):t instanceof Node?this.__commitNode(t):w(t)?this.__commitIterable(t):t===n?(this.value=n,this.clear()):this.__commitText(t))}__insert(t){this.endNode.parentNode.insertBefore(t,this.endNode)}__commitNode(t){this.value!==t&&(this.clear(),this.__insert(t),this.value=t)}__commitText(t){const e=this.startNode.nextSibling,i="string"==typeof(t=null==t?"":t)?t:String(t);e===this.endNode.previousSibling&&3===e.nodeType?e.data=i:this.__commitNode(document.createTextNode(i)),this.value=t}__commitTemplateResult(t){const e=this.options.templateFactory(t);if(this.value instanceof f&&this.value.template===e)this.value.update(t.values);else{const i=new f(e,t.processor,this.options),r=i._clone();i.update(t.values),this.__commitNode(r),this.value=i}}__commitIterable(t){Array.isArray(this.value)||(this.value=[],this.clear());const e=this.value;let i,r=0;for(const s of t)void 0===(i=e[r])&&(i=new x(this.options),e.push(i),0===r?i.appendIntoPart(this):i.insertAfterPart(e[r-1])),i.setValue(s),i.commit(),r++;r<e.length&&(e.length=r,this.clear(i&&i.endNode))}clear(t=this.startNode){s(this.startNode.parentNode,t.nextSibling,this.endNode)}}class P{constructor(t,e,i){if(this.value=void 0,this.__pendingValue=void 0,2!==i.length||""!==i[0]||""!==i[1])throw new Error("Boolean attributes can only contain a single expression");this.element=t,this.name=e,this.strings=i}setValue(t){this.__pendingValue=t}commit(){for(;i(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=o,t(this)}if(this.__pendingValue===o)return;const t=!!this.__pendingValue;this.value!==t&&(t?this.element.setAttribute(this.name,""):this.element.removeAttribute(this.name),this.value=t),this.__pendingValue=o}}class C extends b{constructor(t,e,i){super(t,e,i),this.single=2===i.length&&""===i[0]&&""===i[1]}_createPart(){return new N(this)}_getValue(){return this.single?this.parts[0].value:super._getValue()}commit(){this.dirty&&(this.dirty=!1,this.element[this.name]=this._getValue())}}class N extends S{}let $=!1;try{const t={get capture(){return $=!0,!1}};window.addEventListener("test",t,t),window.removeEventListener("test",t,t)}catch(t){}class k{constructor(t,e,i){this.value=void 0,this.__pendingValue=void 0,this.element=t,this.eventName=e,this.eventContext=i,this.__boundHandleEvent=(t=>this.handleEvent(t))}setValue(t){this.__pendingValue=t}commit(){for(;i(this.__pendingValue);){const t=this.__pendingValue;this.__pendingValue=o,t(this)}if(this.__pendingValue===o)return;const t=this.__pendingValue,e=this.value,r=null==t||null!=e&&(t.capture!==e.capture||t.once!==e.once||t.passive!==e.passive),s=null!=t&&(null==e||r);r&&this.element.removeEventListener(this.eventName,this.__boundHandleEvent,this.__options),s&&(this.__options=A(t),this.element.addEventListener(this.eventName,this.__boundHandleEvent,this.__options)),this.value=t,this.__pendingValue=o}handleEvent(t){"function"==typeof this.value?this.value.call(this.eventContext||this.element,t):this.value.handleEvent(t)}}const A=t=>t&&($?{capture:t.capture,passive:t.passive,once:t.once}:t.capture);const T=new class{handleAttributeExpressions(t,e,i,r){const s=e[0];return"."===s?new C(t,e.slice(1),i).parts:"@"===s?[new k(t,e.slice(1),r.eventContext)]:"?"===s?[new P(t,e.slice(1),i)]:new b(t,e,i).parts}handleTextExpression(t){return new x(t)}};function z(t){let e=E.get(t.type);void 0===e&&(e={stringsArray:new WeakMap,keyString:new Map},E.set(t.type,e));let i=e.stringsArray.get(t.strings);if(void 0!==i)return i;const r=t.strings.join(a);return void 0===(i=e.keyString.get(r))&&(i=new h(t,t.getTemplateElement()),e.keyString.set(r,i)),e.stringsArray.set(t.strings,i),i}const E=new Map,U=new WeakMap;(window.litHtmlVersions||(window.litHtmlVersions=[])).push("1.1.2");const V=(t,...e)=>new y(t,e,"html",T),O=133;function M(t,e){const{element:{content:i},parts:r}=t,s=document.createTreeWalker(i,O,null,!1);let o=q(r),n=r[o],a=-1,p=0;const l=[];let c=null;for(;s.nextNode();){a++;const t=s.currentNode;for(t.previousSibling===c&&(c=null),e.has(t)&&(l.push(t),null===c&&(c=t)),null!==c&&p++;void 0!==n&&n.index===a;)n.index=null!==c?-1:n.index-p,n=r[o=q(r,o)]}l.forEach(t=>t.parentNode.removeChild(t))}const R=t=>{let e=11===t.nodeType?0:1;const i=document.createTreeWalker(t,O,null,!1);for(;i.nextNode();)e++;return e},q=(t,e=-1)=>{for(let i=e+1;i<t.length;i++){const e=t[i];if(u(e))return i}return-1};const j=(t,e)=>`${t}--${e}`;let I=!0;void 0===window.ShadyCSS?I=!1:void 0===window.ShadyCSS.prepareTemplateDom&&(console.warn("Incompatible ShadyCSS version detected. Please update to at least @webcomponents/webcomponentsjs@2.0.2 and @webcomponents/shadycss@1.3.1."),I=!1);const F=t=>e=>{const i=j(e.type,t);let r=E.get(i);void 0===r&&(r={stringsArray:new WeakMap,keyString:new Map},E.set(i,r));let s=r.stringsArray.get(e.strings);if(void 0!==s)return s;const o=e.strings.join(a);if(void 0===(s=r.keyString.get(o))){const i=e.getTemplateElement();I&&window.ShadyCSS.prepareTemplateDom(i,t),s=new h(e,i),r.keyString.set(o,s)}return r.stringsArray.set(e.strings,s),s},H=["html","svg"],B=new Set,L=(t,e,i)=>{B.add(t);const r=i?i.element:document.createElement("template"),s=e.querySelectorAll("style"),{length:o}=s;if(0===o)return void window.ShadyCSS.prepareTemplateStyles(r,t);const n=document.createElement("style");for(let t=0;t<o;t++){const e=s[t];e.parentNode.removeChild(e),n.textContent+=e.textContent}(t=>{H.forEach(e=>{const i=E.get(j(e,t));void 0!==i&&i.keyString.forEach(t=>{const{element:{content:e}}=t,i=new Set;Array.from(e.querySelectorAll("style")).forEach(t=>{i.add(t)}),M(t,i)})})})(t);const a=r.content;i?function(t,e,i=null){const{element:{content:r},parts:s}=t;if(null==i)return void r.appendChild(e);const o=document.createTreeWalker(r,O,null,!1);let n=q(s),a=0,p=-1;for(;o.nextNode();)for(p++,o.currentNode===i&&(a=R(e),i.parentNode.insertBefore(e,i));-1!==n&&s[n].index===p;){if(a>0){for(;-1!==n;)s[n].index+=a,n=q(s,n);return}n=q(s,n)}}(i,n,a.firstChild):a.insertBefore(n,a.firstChild),window.ShadyCSS.prepareTemplateStyles(r,t);const p=a.querySelector("style");if(window.ShadyCSS.nativeShadow&&null!==p)e.insertBefore(p.cloneNode(!0),e.firstChild);else if(i){a.insertBefore(n,a.firstChild);const t=new Set;t.add(n),M(i,t)}},W=(t,e,i)=>{if(!i||"object"!=typeof i||!i.scopeName)throw new Error("The `scopeName` option is required.");const r=i.scopeName,o=U.has(e),n=I&&11===e.nodeType&&!!e.host,a=n&&!B.has(r),p=a?document.createDocumentFragment():e;if(((t,e,i)=>{let r=U.get(e);void 0===r&&(s(e,e.firstChild),U.set(e,r=new x(Object.assign({templateFactory:z},i))),r.appendInto(e)),r.setValue(t),r.commit()})(t,p,Object.assign({templateFactory:F(r)},i)),a){const t=U.get(p);U.delete(p);const i=t.value instanceof f?t.value.template:void 0;L(r,p,i),s(e,e.firstChild),e.appendChild(p),U.set(e,t)}!o&&n&&window.ShadyCSS.styleElement(e.host)};window.JSCompiler_renameProperty=((t,e)=>t);const D={toAttribute(t,e){switch(e){case Boolean:return t?"":null;case Object:case Array:return null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){switch(e){case Boolean:return null!==t;case Number:return null===t?null:Number(t);case Object:case Array:return JSON.parse(t)}return t}},J=(t,e)=>e!==t&&(e==e||t==t),Z={attribute:!0,type:String,converter:D,reflect:!1,hasChanged:J},Q=Promise.resolve(!0),G=1,K=4,X=8,Y=16,tt=32,et="finalized";class it extends HTMLElement{constructor(){super(),this._updateState=0,this._instanceProperties=void 0,this._updatePromise=Q,this._hasConnectedResolver=void 0,this._changedProperties=new Map,this._reflectingProperties=void 0,this.initialize()}static get observedAttributes(){this.finalize();const t=[];return this._classProperties.forEach((e,i)=>{const r=this._attributeNameForProperty(i,e);void 0!==r&&(this._attributeToPropertyMap.set(r,i),t.push(r))}),t}static _ensureClassProperties(){if(!this.hasOwnProperty(JSCompiler_renameProperty("_classProperties",this))){this._classProperties=new Map;const t=Object.getPrototypeOf(this)._classProperties;void 0!==t&&t.forEach((t,e)=>this._classProperties.set(e,t))}}static createProperty(t,e=Z){if(this._ensureClassProperties(),this._classProperties.set(t,e),e.noAccessor||this.prototype.hasOwnProperty(t))return;const i="symbol"==typeof t?Symbol():`__${t}`;Object.defineProperty(this.prototype,t,{get(){return this[i]},set(e){const r=this[t];this[i]=e,this._requestUpdate(t,r)},configurable:!0,enumerable:!0})}static finalize(){const t=Object.getPrototypeOf(this);if(t.hasOwnProperty(et)||t.finalize(),this[et]=!0,this._ensureClassProperties(),this._attributeToPropertyMap=new Map,this.hasOwnProperty(JSCompiler_renameProperty("properties",this))){const t=this.properties,e=[...Object.getOwnPropertyNames(t),..."function"==typeof Object.getOwnPropertySymbols?Object.getOwnPropertySymbols(t):[]];for(const i of e)this.createProperty(i,t[i])}}static _attributeNameForProperty(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}static _valueHasChanged(t,e,i=J){return i(t,e)}static _propertyValueFromAttribute(t,e){const i=e.type,r=e.converter||D,s="function"==typeof r?r:r.fromAttribute;return s?s(t,i):t}static _propertyValueToAttribute(t,e){if(void 0===e.reflect)return;const i=e.type,r=e.converter;return(r&&r.toAttribute||D.toAttribute)(t,i)}initialize(){this._saveInstanceProperties(),this._requestUpdate()}_saveInstanceProperties(){this.constructor._classProperties.forEach((t,e)=>{if(this.hasOwnProperty(e)){const t=this[e];delete this[e],this._instanceProperties||(this._instanceProperties=new Map),this._instanceProperties.set(e,t)}})}_applyInstanceProperties(){this._instanceProperties.forEach((t,e)=>this[e]=t),this._instanceProperties=void 0}connectedCallback(){this._updateState=this._updateState|tt,this._hasConnectedResolver&&(this._hasConnectedResolver(),this._hasConnectedResolver=void 0)}disconnectedCallback(){}attributeChangedCallback(t,e,i){e!==i&&this._attributeToProperty(t,i)}_propertyToAttribute(t,e,i=Z){const r=this.constructor,s=r._attributeNameForProperty(t,i);if(void 0!==s){const t=r._propertyValueToAttribute(e,i);if(void 0===t)return;this._updateState=this._updateState|X,null==t?this.removeAttribute(s):this.setAttribute(s,t),this._updateState=this._updateState&~X}}_attributeToProperty(t,e){if(this._updateState&X)return;const i=this.constructor,r=i._attributeToPropertyMap.get(t);if(void 0!==r){const t=i._classProperties.get(r)||Z;this._updateState=this._updateState|Y,this[r]=i._propertyValueFromAttribute(e,t),this._updateState=this._updateState&~Y}}_requestUpdate(t,e){let i=!0;if(void 0!==t){const r=this.constructor,s=r._classProperties.get(t)||Z;r._valueHasChanged(this[t],e,s.hasChanged)?(this._changedProperties.has(t)||this._changedProperties.set(t,e),!0!==s.reflect||this._updateState&Y||(void 0===this._reflectingProperties&&(this._reflectingProperties=new Map),this._reflectingProperties.set(t,s))):i=!1}!this._hasRequestedUpdate&&i&&this._enqueueUpdate()}requestUpdate(t,e){return this._requestUpdate(t,e),this.updateComplete}async _enqueueUpdate(){let t,e;this._updateState=this._updateState|K;const i=this._updatePromise;this._updatePromise=new Promise((i,r)=>{t=i,e=r});try{await i}catch(t){}this._hasConnected||await new Promise(t=>this._hasConnectedResolver=t);try{const t=this.performUpdate();null!=t&&await t}catch(t){e(t)}t(!this._hasRequestedUpdate)}get _hasConnected(){return this._updateState&tt}get _hasRequestedUpdate(){return this._updateState&K}get hasUpdated(){return this._updateState&G}performUpdate(){this._instanceProperties&&this._applyInstanceProperties();let t=!1;const e=this._changedProperties;try{(t=this.shouldUpdate(e))&&this.update(e)}catch(e){throw t=!1,e}finally{this._markUpdated()}t&&(this._updateState&G||(this._updateState=this._updateState|G,this.firstUpdated(e)),this.updated(e))}_markUpdated(){this._changedProperties=new Map,this._updateState=this._updateState&~K}get updateComplete(){return this._getUpdateComplete()}_getUpdateComplete(){return this._updatePromise}shouldUpdate(t){return!0}update(t){void 0!==this._reflectingProperties&&this._reflectingProperties.size>0&&(this._reflectingProperties.forEach((t,e)=>this._propertyToAttribute(e,this[e],t)),this._reflectingProperties=void 0)}updated(t){}firstUpdated(t){}}it[et]=!0;const rt=t=>e=>"function"==typeof e?((t,e)=>(window.customElements.define(t,e),e))(t,e):((t,e)=>{const{kind:i,elements:r}=e;return{kind:i,elements:r,finisher(e){window.customElements.define(t,e)}}})(t,e),st=(t,e)=>"method"!==e.kind||!e.descriptor||"value"in e.descriptor?{kind:"field",key:Symbol(),placement:"own",descriptor:{},initializer(){"function"==typeof e.initializer&&(this[e.key]=e.initializer.call(this))},finisher(i){i.createProperty(e.key,t)}}:Object.assign({},e,{finisher(i){i.createProperty(e.key,t)}}),ot=(t,e,i)=>{e.constructor.createProperty(i,t)};function nt(t){return(e,i)=>void 0!==i?ot(t,e,i):st(t,e)}const at="adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,pt=Symbol();class lt{constructor(t,e){if(e!==pt)throw new Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t}get styleSheet(){return void 0===this._styleSheet&&(at?(this._styleSheet=new CSSStyleSheet,this._styleSheet.replaceSync(this.cssText)):this._styleSheet=null),this._styleSheet}toString(){return this.cssText}}const ct=(t,...e)=>{const i=e.reduce((e,i,r)=>e+(t=>{if(t instanceof lt)return t.cssText;if("number"==typeof t)return t;throw new Error(`Value passed to 'css' function must be a 'css' function result: ${t}. Use 'unsafeCSS' to pass non-literal values, but\n            take care to ensure page security.`)})(i)+t[r+1],t[0]);return new lt(i,pt)};(window.litElementVersions||(window.litElementVersions=[])).push("2.2.1");const ht=t=>t.flat?t.flat(1/0):function t(e,i=[]){for(let r=0,s=e.length;r<s;r++){const s=e[r];Array.isArray(s)?t(s,i):i.push(s)}return i}(t);class dt extends it{static finalize(){super.finalize.call(this),this._styles=this.hasOwnProperty(JSCompiler_renameProperty("styles",this))?this._getUniqueStyles():this._styles||[]}static _getUniqueStyles(){const t=this.styles,e=[];if(Array.isArray(t)){ht(t).reduceRight((t,e)=>(t.add(e),t),new Set).forEach(t=>e.unshift(t))}else t&&e.push(t);return e}initialize(){super.initialize(),this.renderRoot=this.createRenderRoot(),window.ShadowRoot&&this.renderRoot instanceof window.ShadowRoot&&this.adoptStyles()}createRenderRoot(){return this.attachShadow({mode:"open"})}adoptStyles(){const t=this.constructor._styles;0!==t.length&&(void 0===window.ShadyCSS||window.ShadyCSS.nativeShadow?at?this.renderRoot.adoptedStyleSheets=t.map(t=>t.styleSheet):this._needsShimAdoptedStyleSheets=!0:window.ShadyCSS.ScopingShim.prepareAdoptedCssText(t.map(t=>t.cssText),this.localName))}connectedCallback(){super.connectedCallback(),this.hasUpdated&&void 0!==window.ShadyCSS&&window.ShadyCSS.styleElement(this)}update(t){super.update(t);const e=this.render();e instanceof y&&this.constructor.render(e,this.renderRoot,{scopeName:this.localName,eventContext:this}),this._needsShimAdoptedStyleSheets&&(this._needsShimAdoptedStyleSheets=!1,this.constructor._styles.forEach(t=>{const e=document.createElement("style");e.textContent=t.cssText,this.renderRoot.appendChild(e)}))}render(){}}dt.finalized=!0,dt.render=W;const ut=(t,e,i=!0)=>{i?history.replaceState(null,"",e):history.pushState(null,"",e)},mt=t=>null!==t,gt=t=>t?"":null,ft=(t,e)=>e!==t&&(e==e||t==t),_t={attribute:!0,type:String,reflect:!1,hasChanged:ft},yt=new Promise(t=>t(!0)),vt=1,wt=4,bt=8;class St extends HTMLElement{constructor(){super(),this._updateState=0,this._instanceProperties=void 0,this._updatePromise=yt,this._changedProperties=new Map,this._reflectingProperties=void 0,this.initialize()}static get observedAttributes(){this._finalize();const t=[];for(const[e,i]of this._classProperties){const r=this._attributeNameForProperty(e,i);void 0!==r&&(this._attributeToPropertyMap.set(r,e),t.push(r))}return t}static createProperty(t,e=_t){if(!this.hasOwnProperty("_classProperties")){this._classProperties=new Map;const t=Object.getPrototypeOf(this)._classProperties;void 0!==t&&t.forEach((t,e)=>this._classProperties.set(e,t))}if(this._classProperties.set(t,e),this.prototype.hasOwnProperty(t))return;const i="symbol"==typeof t?Symbol():`__${t}`;Object.defineProperty(this.prototype,t,{get(){return this[i]},set(r){const s=this[t];this[i]=r,this._requestPropertyUpdate(t,s,e)},configurable:!0,enumerable:!0})}static _finalize(){if(this.hasOwnProperty("_finalized")&&this._finalized)return;const t=Object.getPrototypeOf(this);"function"==typeof t._finalize&&t._finalize(),this._finalized=!0,this._attributeToPropertyMap=new Map;const e=this.properties,i=[...Object.getOwnPropertyNames(e),..."function"==typeof Object.getOwnPropertySymbols?Object.getOwnPropertySymbols(e):[]];for(const t of i)this.createProperty(t,e[t])}static _attributeNameForProperty(t,e){const i=void 0!==e&&e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}static _valueHasChanged(t,e,i=ft){return i(t,e)}static _propertyValueFromAttribute(t,e){const i=e&&e.type;if(void 0===i)return t;const r=i===Boolean?mt:"function"==typeof i?i:i.fromAttribute;return r?r(t):t}static _propertyValueToAttribute(t,e){if(void 0===e||void 0===e.reflect)return;return(e.type===Boolean?gt:e.type&&e.type.toAttribute||String)(t)}initialize(){this.renderRoot=this.createRenderRoot(),this._saveInstanceProperties()}_saveInstanceProperties(){for(const[t]of this.constructor._classProperties)if(this.hasOwnProperty(t)){const e=this[t];delete this[t],this._instanceProperties||(this._instanceProperties=new Map),this._instanceProperties.set(t,e)}}_applyInstanceProperties(){for(const[t,e]of this._instanceProperties)this[t]=e;this._instanceProperties=void 0}createRenderRoot(){return this.attachShadow({mode:"open"})}connectedCallback(){this._updateState&vt?void 0!==window.ShadyCSS&&window.ShadyCSS.styleElement(this):this.requestUpdate()}disconnectedCallback(){}attributeChangedCallback(t,e,i){e!==i&&this._attributeToProperty(t,i)}_propertyToAttribute(t,e,i=_t){const r=this.constructor,s=r._propertyValueToAttribute(e,i);if(void 0!==s){const e=r._attributeNameForProperty(t,i);void 0!==e&&(this._updateState=this._updateState|bt,null===s?this.removeAttribute(e):this.setAttribute(e,s),this._updateState=this._updateState&~bt)}}_attributeToProperty(t,e){if(!(this._updateState&bt)){const i=this.constructor,r=i._attributeToPropertyMap.get(t);if(void 0!==r){const t=i._classProperties.get(r);this[r]=i._propertyValueFromAttribute(e,t)}}}requestUpdate(t,e){if(void 0!==t){const i=this.constructor._classProperties.get(t)||_t;return this._requestPropertyUpdate(t,e,i)}return this._invalidate()}_requestPropertyUpdate(t,e,i){return this.constructor._valueHasChanged(this[t],e,i.hasChanged)?(this._changedProperties.has(t)||this._changedProperties.set(t,e),!0===i.reflect&&(void 0===this._reflectingProperties&&(this._reflectingProperties=new Map),this._reflectingProperties.set(t,i)),this._invalidate()):this.updateComplete}async _invalidate(){if(!this._hasRequestedUpdate){let t;this._updateState=this._updateState|wt;const e=this._updatePromise;this._updatePromise=new Promise(e=>t=e),await e,this._validate(),t(!this._hasRequestedUpdate)}return this.updateComplete}get _hasRequestedUpdate(){return this._updateState&wt}_validate(){if(this._instanceProperties&&this._applyInstanceProperties(),this.shouldUpdate(this._changedProperties)){const t=this._changedProperties;this.update(t),this._markUpdated(),this._updateState&vt||(this._updateState=this._updateState|vt,this.firstUpdated(t)),this.updated(t)}else this._markUpdated()}_markUpdated(){this._changedProperties=new Map,this._updateState=this._updateState&~wt}get updateComplete(){return this._updatePromise}shouldUpdate(t){return!0}update(t){if(void 0!==this._reflectingProperties&&this._reflectingProperties.size>0){for(const[t,e]of this._reflectingProperties)this._propertyToAttribute(t,this[t],e);this._reflectingProperties=void 0}}updated(t){}firstUpdated(t){}}St._attributeToPropertyMap=new Map,St._finalized=!0,St._classProperties=new Map,St.properties={};class xt extends St{update(t){super.update(t);const e=this.render();e instanceof y&&this.constructor.render(e,this.renderRoot,{scopeName:this.localName,eventContext:this})}render(){}}xt.render=W;window.customElements.define("granite-spinner",class extends xt{static get properties(){return{active:{type:Boolean,reflect:!0},hover:{type:Boolean,reflect:!0},size:{type:Number},color:{type:String},lineWidth:{type:String},containerHeight:{type:Number,value:150},debug:{type:Boolean}}}constructor(){super(),this.size=100,this.color="#28b6d8",this.lineWidth="1.5em",this.containerHeight=150}firstUpdated(){this.debug&&console.log("[granite-spinner] firstUpdated")}shouldUpdate(){return this.debug&&console.log("[granite-spinner] shouldUpdate",this.lineWidth),!0}render(){if(this.active)return V`
      ${this._renderStyles()}      
      <div id="spinner-container">
        <div id="spinner" class="loading">
        </div>
      </div>
    `}_renderStyles(){return V`
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
      
    `}});let Pt=class extends dt{render(){return V`
            <granite-spinner color="var(--primary-color)" active hover size=400 containerHeight=100%></granite-spinner>
            `}};Pt=t([rt("hacs-spinner")],Pt);let Ct=class extends dt{render(){var t=this.repositories.content||[];return t=this.repositories.content.filter(function(t){return t.installed}),V`
    <div class="hacs-repositories">
    ${t.map(t=>V`<ha-card header="${t.name}">
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
      `}};t([nt()],Ct.prototype,"hass",void 0),t([nt()],Ct.prototype,"repositories",void 0),t([nt()],Ct.prototype,"configuration",void 0),Ct=t([rt("hacs-panel-installed")],Ct);let Nt=class extends dt{constructor(){super(...arguments),this.repository_view=!1}render(){const t=this.panel,e=this.configuration;var i=this.repositories.content||[];return i=this.repositories.content.filter(function(i){if("installed"!==t){if("172733314"===i.id)return!1;if(i.hide)return!1;if(null!==e.country&&e.country!==i.country)return!1}return i.category===t}),V`
    <div class="card-group">
    ${i.sort((t,e)=>t.name>e.name?1:-1).map(t=>V`

      <paper-card @click="${this.getQuote}" RepoID="${t.id}">
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
          `}getQuote(t){t.path.forEach(t=>{void 0!==t.RepoID&&(this.panel=`repository/${t.RepoID}`,this.repository_view=!0,ut(0,`/hacs/repository/${t.RepoID}`),this.requestUpdate(),window.location.reload())})}static get styles(){return ct`
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
    `}};t([nt()],Nt.prototype,"hass",void 0),t([nt()],Nt.prototype,"repositories",void 0),t([nt()],Nt.prototype,"configuration",void 0),t([nt()],Nt.prototype,"panel",void 0),t([nt()],Nt.prototype,"repository_view",void 0),Nt=t([rt("hacs-panel-store")],Nt);let $t=class extends dt{render(){return console.log("hass: ",this.hass),console.log("configuration: ",this.configuration),V`

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
      `}};t([nt()],$t.prototype,"hass",void 0),t([nt()],$t.prototype,"repositories",void 0),t([nt()],$t.prototype,"configuration",void 0),$t=t([rt("hacs-panel-settings")],$t);let kt=class extends dt{render(){var t=this.repository,e=(this.repositories.content,this.repositories.content.filter(function(e){return e.id===t})[0]);return V`

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
      `}};t([nt()],kt.prototype,"hass",void 0),t([nt()],kt.prototype,"repositories",void 0),t([nt()],kt.prototype,"configuration",void 0),t([nt()],kt.prototype,"repository",void 0),kt=t([rt("hacs-panel-repository")],kt);let At=class extends dt{constructor(){super(...arguments),this.repository_view=!1}getRepositories(){this.hass.connection.sendMessagePromise({type:"hacs/config"}).then(t=>{this.configuration=t},t=>{console.error("Message failed!",t)}),this.hass.connection.sendMessagePromise({type:"hacs/repositories"}).then(t=>{this.repositories=t},t=>{console.error("Message failed!",t)}),this.requestUpdate()}firstUpdated(){this.panel=this._page,this.getRepositories(),this.addEventListener("location-changed",async t=>{console.log(t),console.log(await this.requestUpdate())}),function(){if(customElements.get("hui-view"))return!0;const t=document.createElement("partial-panel-resolver");t.hass=document.querySelector("home-assistant").hass,t.route={path:"/lovelace/"};try{document.querySelector("home-assistant").appendChild(t).catch(t=>{})}catch(e){document.querySelector("home-assistant").removeChild(t)}customElements.get("hui-view")}()}render(){if(""===this.panel&&(ut(0,"/hacs/installed"),this.panel="installed"),console.log(this.panel),void 0===this.repositories)return V`<hacs-spinner></hacs-spinner>`;if(/repository\//i.test(this.panel)){this.repository_view=!0;var t=this.panel.split("/")[1]}return V`
    <app-header-layout has-scrolling-region>
    <app-header slot="header" fixed>
      <app-toolbar>
        <ha-menu-button .hass="${this.hass}" .narrow="${this.narrow}"></ha-menu-button>
        <div main-title>${this.hass.localize("component.hacs.config.title")}</div>
      </app-toolbar>
    </app-header>
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

    ${this.configuration.appdaemon?V`<paper-tab page-name="appdaemon">
        ${this.hass.localize("component.hacs.common.appdaemon_apps")}
    </paper-tab>`:""}

    ${this.configuration.python_script?V`<paper-tab page-name="python_script">
        ${this.hass.localize("component.hacs.common.python_scripts")}
    </paper-tab>`:""}

    ${this.configuration.theme?V`<paper-tab page-name="theme">
        ${this.hass.localize("component.hacs.common.themes")}
    </paper-tab>`:""}

    <paper-tab class="right" page-name="settings">
    ${this.hass.localize("component.hacs.common.settings")}
    </paper-tab>

    </paper-tabs>

    ${this.repository_view?V`
    <hacs-panel-repository
    .hass=${this.hass}
    .configuration=${this.configuration}
    .repositories=${this.repositories}
    .repository=${t}>
    </hacs-panel-repository>`:""}

    ${"installed"===this.panel?V`
      <hacs-panel-installed
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repositories=${this.repositories}>
        </hacs-panel-installed>`:""}

    ${this.panel,V`
    <hacs-panel-store
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .panel=${this.panel}
      .repository_view=${this.repository_view}>
      </hacs-panel-store>`}

    ${"settings"===this.panel?V`
      <hacs-panel-settings
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repositories=${this.repositories}>
        </hacs-panel-settings>`:""}

    </app-header-layout>`}handlePageSelected(t){this.repository_view=!1;const e=t.detail.item.getAttribute("page-name");this.panel=e,ut(0,`/hacs/${e}`),this.requestUpdate()}get _page(){return null===this.route.path.substr(1)?"installed":this.route.path.substr(1)}static get styles(){return ct`
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
    `}};t([nt()],At.prototype,"hass",void 0),t([nt()],At.prototype,"repositories",void 0),t([nt()],At.prototype,"configuration",void 0),t([nt()],At.prototype,"route",void 0),t([nt()],At.prototype,"narrow",void 0),t([nt()],At.prototype,"panel",void 0),t([nt()],At.prototype,"repository_view",void 0),At=t([rt("hacs-frontend")],At);
