window.JSCompiler_renameProperty=function(e,t){return e};let e,t,i=/(url\()([^)]*)(\))/g,n=/(^\/[^\/])|(^#)|(^[\w-\d]*:)/;function r(i,r){if(i&&n.test(i))return i;if("//"===i)return i;if(void 0===e){e=!1;try{const t=new URL("b","http://a");t.pathname="c%20d",e="http://a/c%20d"===t.href}catch(e){}}if(r||(r=document.baseURI||window.location.href),e)try{return new URL(i,r).href}catch(e){return i}return t||((t=document.implementation.createHTMLDocument("temp")).base=t.createElement("base"),t.head.appendChild(t.base),t.anchor=t.createElement("a"),t.body.appendChild(t.anchor)),t.base.href=r,t.anchor.href=i,t.anchor.href||i}function s(e,t){return e.replace(i,function(e,i,n,s){return i+"'"+r(n.replace(/["']/g,""),t)+"'"+s})}function o(e){return e.substring(0,e.lastIndexOf("/")+1)}const a=!window.ShadyDOM;Boolean(!window.ShadyCSS||window.ShadyCSS.nativeCss);let l=o(document.baseURI||window.location.href),h=window.Polymer&&window.Polymer.sanitizeDOMValue||void 0,p=!1,c=!1,d=!1,u=!1,f=!1,_=!0,m=0;const y=function(e){let t=e.__mixinApplications;t||(t=new WeakMap,e.__mixinApplications=t);let i=m++;return function(n){let r=n.__mixinSet;if(r&&r[i])return n;let s=t,o=s.get(n);o||(o=e(n),s.set(n,o));let a=Object.create(o.__mixinSet||r||null);return a[i]=!0,o.__mixinSet=a,o}};let g={},b={};function v(e,t){g[e]=b[e.toLowerCase()]=t}function w(e){return g[e]||b[e.toLowerCase()]}class C extends HTMLElement{static get observedAttributes(){return["id"]}static import(e,t){if(e){let i=w(e);return i&&t?i.querySelector(t):i}return null}attributeChangedCallback(e,t,i,n){t!==i&&this.register()}get assetpath(){if(!this.__assetpath){const e=window.HTMLImports&&HTMLImports.importForElement?HTMLImports.importForElement(this)||document:this.ownerDocument,t=r(this.getAttribute("assetpath")||"",e.baseURI);this.__assetpath=o(t)}return this.__assetpath}register(e){if(e=e||this.id){if(c&&void 0!==w(e))throw v(e,null),new Error(`strictTemplatePolicy: dom-module ${e} re-registered`);this.id=e,v(e,this),(t=this).querySelector("style")&&console.warn("dom-module %s has style outside template",t.id)}var t}}C.prototype.modules=g,customElements.define("dom-module",C);const x="link[rel=import][type~=css]",P="include",S="shady-unscoped";function O(e){return C.import(e)}function E(e){const t=s((e.body?e.body:e).textContent,e.baseURI),i=document.createElement("style");return i.textContent=t,i}function T(e){const t=e.trim().split(/\s+/),i=[];for(let e=0;e<t.length;e++)i.push(...A(t[e]));return i}function A(e){const t=O(e);if(!t)return console.warn("Could not find style data in module named",e),[];if(void 0===t._styles){const e=[];e.push(...k(t));const i=t.querySelector("template");i&&e.push(...N(i,t.assetpath)),t._styles=e}return t._styles}function N(e,t){if(!e._styles){const i=[],n=e.content.querySelectorAll("style");for(let e=0;e<n.length;e++){let r=n[e],o=r.getAttribute(P);o&&i.push(...T(o).filter(function(e,t,i){return i.indexOf(e)===t})),t&&(r.textContent=s(r.textContent,t)),i.push(r)}e._styles=i}return e._styles}function k(e){const t=[],i=e.querySelectorAll(x);for(let e=0;e<i.length;e++){let n=i[e];if(n.import){const e=n.import,i=n.hasAttribute(S);if(i&&!e._unscopedStyle){const t=E(e);t.setAttribute(S,""),e._unscopedStyle=t}else e._style||(e._style=E(e));t.push(i?e._unscopedStyle:e._style)}}return t}function I(e){let t=O(e);if(t&&void 0===t._cssText){let e=function(e){let t="",i=k(e);for(let e=0;e<i.length;e++)t+=i[e].textContent;return t}(t),i=t.querySelector("template");i&&(e+=function(e,t){let i="";const n=N(e,t);for(let e=0;e<n.length;e++){let t=n[e];t.parentNode&&t.parentNode.removeChild(t),i+=t.textContent}return i}(i,t.assetpath)),t._cssText=e||null}return t||console.warn("Could not find style data in module named",e),t&&t._cssText||""}const R=window.ShadyDOM&&window.ShadyDOM.noPatch&&window.ShadyDOM.wrap?window.ShadyDOM.wrap:window.ShadyDOM?e=>ShadyDOM.patch(e):e=>e;function z(e){return e.indexOf(".")>=0}function M(e){let t=e.indexOf(".");return-1===t?e:e.slice(0,t)}function L(e,t){return 0===e.indexOf(t+".")}function D(e,t){return 0===t.indexOf(e+".")}function F(e,t,i){return t+i.slice(e.length)}function B(e){if(Array.isArray(e)){let t=[];for(let i=0;i<e.length;i++){let n=e[i].toString().split(".");for(let e=0;e<n.length;e++)t.push(n[e])}return t.join(".")}return e}function H(e){return Array.isArray(e)?B(e).split("."):e.toString().split(".")}function j(e,t,i){let n=e,r=H(t);for(let e=0;e<r.length;e++){if(!n)return;n=n[r[e]]}return i&&(i.path=r.join(".")),n}function $(e,t,i){let n=e,r=H(t),s=r[r.length-1];if(r.length>1){for(let e=0;e<r.length-1;e++){if(!(n=n[r[e]]))return}n[s]=i}else n[t]=i;return r.join(".")}const q={},Y=/-[a-z]/g,U=/([A-Z])/g;function V(e){return q[e]||(q[e]=e.indexOf("-")<0?e:e.replace(Y,e=>e[1].toUpperCase()))}function X(e){return q[e]||(q[e]=e.replace(U,"-$1").toLowerCase())}let J=0,W=0,Z=[],K=0,G=document.createTextNode("");new window.MutationObserver(function(){const e=Z.length;for(let t=0;t<e;t++){let e=Z[t];if(e)try{e()}catch(e){setTimeout(()=>{throw e})}}Z.splice(0,e),W+=e}).observe(G,{characterData:!0});const Q={after:e=>({run:t=>window.setTimeout(t,e),cancel(e){window.clearTimeout(e)}}),run:(e,t)=>window.setTimeout(e,t),cancel(e){window.clearTimeout(e)}},ee={run:e=>(G.textContent=K++,Z.push(e),J++),cancel(e){const t=e-W;if(t>=0){if(!Z[t])throw new Error("invalid async handle: "+e);Z[t]=null}}},te=ee,ie=y(e=>{return class extends e{static createProperties(e){const t=this.prototype;for(let i in e)i in t||t._createPropertyAccessor(i)}static attributeNameForProperty(e){return e.toLowerCase()}static typeForProperty(e){}_createPropertyAccessor(e,t){this._addPropertyToAttributeMap(e),this.hasOwnProperty("__dataHasAccessor")||(this.__dataHasAccessor=Object.assign({},this.__dataHasAccessor)),this.__dataHasAccessor[e]||(this.__dataHasAccessor[e]=!0,this._definePropertyAccessor(e,t))}_addPropertyToAttributeMap(e){if(this.hasOwnProperty("__dataAttributes")||(this.__dataAttributes=Object.assign({},this.__dataAttributes)),!this.__dataAttributes[e]){const t=this.constructor.attributeNameForProperty(e);this.__dataAttributes[t]=e}}_definePropertyAccessor(e,t){Object.defineProperty(this,e,{get(){return this._getProperty(e)},set:t?function(){}:function(t){this._setProperty(e,t)}})}constructor(){super(),this.__dataEnabled=!1,this.__dataReady=!1,this.__dataInvalid=!1,this.__data={},this.__dataPending=null,this.__dataOld=null,this.__dataInstanceProps=null,this.__serializing=!1,this._initializeProperties()}ready(){this.__dataReady=!0,this._flushProperties()}_initializeProperties(){for(let e in this.__dataHasAccessor)this.hasOwnProperty(e)&&(this.__dataInstanceProps=this.__dataInstanceProps||{},this.__dataInstanceProps[e]=this[e],delete this[e])}_initializeInstanceProperties(e){Object.assign(this,e)}_setProperty(e,t){this._setPendingProperty(e,t)&&this._invalidateProperties()}_getProperty(e){return this.__data[e]}_setPendingProperty(e,t,i){let n=this.__data[e],r=this._shouldPropertyChange(e,t,n);return r&&(this.__dataPending||(this.__dataPending={},this.__dataOld={}),!this.__dataOld||e in this.__dataOld||(this.__dataOld[e]=n),this.__data[e]=t,this.__dataPending[e]=t),r}_invalidateProperties(){!this.__dataInvalid&&this.__dataReady&&(this.__dataInvalid=!0,te.run(()=>{this.__dataInvalid&&(this.__dataInvalid=!1,this._flushProperties())}))}_enableProperties(){this.__dataEnabled||(this.__dataEnabled=!0,this.__dataInstanceProps&&(this._initializeInstanceProperties(this.__dataInstanceProps),this.__dataInstanceProps=null),this.ready())}_flushProperties(){const e=this.__data,t=this.__dataPending,i=this.__dataOld;this._shouldPropertiesChange(e,t,i)&&(this.__dataPending=null,this.__dataOld=null,this._propertiesChanged(e,t,i))}_shouldPropertiesChange(e,t,i){return Boolean(t)}_propertiesChanged(e,t,i){}_shouldPropertyChange(e,t,i){return i!==t&&(i==i||t==t)}attributeChangedCallback(e,t,i,n){t!==i&&this._attributeToProperty(e,i),super.attributeChangedCallback&&super.attributeChangedCallback(e,t,i,n)}_attributeToProperty(e,t,i){if(!this.__serializing){const n=this.__dataAttributes,r=n&&n[e]||e;this[r]=this._deserializeValue(t,i||this.constructor.typeForProperty(r))}}_propertyToAttribute(e,t,i){this.__serializing=!0,i=arguments.length<3?this[e]:i,this._valueToNodeAttribute(this,i,t||this.constructor.attributeNameForProperty(e)),this.__serializing=!1}_valueToNodeAttribute(e,t,i){const n=this._serializeValue(t);"class"!==i&&"name"!==i&&"slot"!==i||(e=R(e)),void 0===n?e.removeAttribute(i):e.setAttribute(i,n)}_serializeValue(e){switch(typeof e){case"boolean":return e?"":void 0;default:return null!=e?e.toString():void 0}}_deserializeValue(e,t){switch(t){case Boolean:return null!==e;case Number:return Number(e);default:return e}}}}),ne={};let re=HTMLElement.prototype;for(;re;){let e=Object.getOwnPropertyNames(re);for(let t=0;t<e.length;t++)ne[e[t]]=!0;re=Object.getPrototypeOf(re)}const se=y(e=>{const t=ie(e);return class extends t{static createPropertiesForAttributes(){let e=this.observedAttributes;for(let t=0;t<e.length;t++)this.prototype._createPropertyAccessor(V(e[t]))}static attributeNameForProperty(e){return X(e)}_initializeProperties(){this.__dataProto&&(this._initializeProtoProperties(this.__dataProto),this.__dataProto=null),super._initializeProperties()}_initializeProtoProperties(e){for(let t in e)this._setProperty(t,e[t])}_ensureAttribute(e,t){const i=this;i.hasAttribute(e)||this._valueToNodeAttribute(i,t,e)}_serializeValue(e){switch(typeof e){case"object":if(e instanceof Date)return e.toString();if(e)try{return JSON.stringify(e)}catch(e){return""}default:return super._serializeValue(e)}}_deserializeValue(e,t){let i;switch(t){case Object:try{i=JSON.parse(e)}catch(t){i=e}break;case Array:try{i=JSON.parse(e)}catch(t){i=null,console.warn(`Polymer::Attributes: couldn't decode Array as JSON: ${e}`)}break;case Date:i=isNaN(e)?String(e):Number(e),i=new Date(i);break;default:i=super._deserializeValue(e,t)}return i}_definePropertyAccessor(e,t){!function(e,t){if(!ne[t]){let i=e[t];void 0!==i&&(e.__data?e._setPendingProperty(t,i):(e.__dataProto?e.hasOwnProperty(JSCompiler_renameProperty("__dataProto",e))||(e.__dataProto=Object.create(e.__dataProto)):e.__dataProto={},e.__dataProto[t]=i))}}(this,e),super._definePropertyAccessor(e,t)}_hasAccessor(e){return this.__dataHasAccessor&&this.__dataHasAccessor[e]}_isPropertyPending(e){return Boolean(this.__dataPending&&e in this.__dataPending)}}}),oe={"dom-if":!0,"dom-repeat":!0};function ae(e){let t=e.getAttribute("is");if(t&&oe[t]){let i=e;for(i.removeAttribute("is"),e=i.ownerDocument.createElement(t),i.parentNode.replaceChild(e,i),e.appendChild(i);i.attributes.length;)e.setAttribute(i.attributes[0].name,i.attributes[0].value),i.removeAttribute(i.attributes[0].name)}return e}function le(e,t){let i=t.parentInfo&&le(e,t.parentInfo);if(!i)return e;for(let e=i.firstChild,n=0;e;e=e.nextSibling)if(t.parentIndex===n++)return e}function he(e,t,i,n){n.id&&(t[n.id]=i)}function pe(e,t,i){if(i.events&&i.events.length)for(let n,r=0,s=i.events;r<s.length&&(n=s[r]);r++)e._addMethodEventListenerToNode(t,n.name,n.value,e)}function ce(e,t,i){i.templateInfo&&(t._templateInfo=i.templateInfo)}const de=y(e=>{return class extends e{static _parseTemplate(e,t){if(!e._templateInfo){let i=e._templateInfo={};i.nodeInfoList=[],i.stripWhiteSpace=t&&t.stripWhiteSpace||e.hasAttribute("strip-whitespace"),this._parseTemplateContent(e,i,{parent:null})}return e._templateInfo}static _parseTemplateContent(e,t,i){return this._parseTemplateNode(e.content,t,i)}static _parseTemplateNode(e,t,i){let n=!1,r=e;return"template"!=r.localName||r.hasAttribute("preserve-content")?"slot"===r.localName&&(t.hasInsertionPoint=!0):n=this._parseTemplateNestedTemplate(r,t,i)||n,r.firstChild&&this._parseTemplateChildNodes(r,t,i),r.hasAttributes&&r.hasAttributes()&&(n=this._parseTemplateNodeAttributes(r,t,i)||n),n}static _parseTemplateChildNodes(e,t,i){if("script"!==e.localName&&"style"!==e.localName)for(let n,r=e.firstChild,s=0;r;r=n){if("template"==r.localName&&(r=ae(r)),n=r.nextSibling,r.nodeType===Node.TEXT_NODE){let i=n;for(;i&&i.nodeType===Node.TEXT_NODE;)r.textContent+=i.textContent,n=i.nextSibling,e.removeChild(i),i=n;if(t.stripWhiteSpace&&!r.textContent.trim()){e.removeChild(r);continue}}let o={parentIndex:s,parentInfo:i};this._parseTemplateNode(r,t,o)&&(o.infoIndex=t.nodeInfoList.push(o)-1),r.parentNode&&s++}}static _parseTemplateNestedTemplate(e,t,i){let n=e,r=this._parseTemplate(n,t);return(r.content=n.content.ownerDocument.createDocumentFragment()).appendChild(n.content),i.templateInfo=r,!0}static _parseTemplateNodeAttributes(e,t,i){let n=!1,r=Array.from(e.attributes);for(let s,o=r.length-1;s=r[o];o--)n=this._parseTemplateNodeAttribute(e,t,i,s.name,s.value)||n;return n}static _parseTemplateNodeAttribute(e,t,i,n,r){return"on-"===n.slice(0,3)?(e.removeAttribute(n),i.events=i.events||[],i.events.push({name:n.slice(3),value:r}),!0):"id"===n&&(i.id=r,!0)}static _contentForTemplate(e){let t=e._templateInfo;return t&&t.content||e.content}_stampTemplate(e){e&&!e.content&&window.HTMLTemplateElement&&HTMLTemplateElement.decorate&&HTMLTemplateElement.decorate(e);let t=this.constructor._parseTemplate(e),i=t.nodeInfoList,n=t.content||e.content,r=document.importNode(n,!0);r.__noInsertionPoint=!t.hasInsertionPoint;let s=r.nodeList=new Array(i.length);r.$={};for(let e,t=0,n=i.length;t<n&&(e=i[t]);t++){let i=s[t]=le(r,e);he(0,r.$,i,e),ce(0,i,e),pe(this,i,e)}return r=r}_addMethodEventListenerToNode(e,t,i,n){let r=function(e,t,i){return e=e._methodHost||e,function(t){e[i]?e[i](t,t.detail):console.warn("listener method `"+i+"` not defined")}}(n=n||e,0,i);return this._addEventListenerToNode(e,t,r),r}_addEventListenerToNode(e,t,i){e.addEventListener(t,i)}_removeEventListenerFromNode(e,t,i){e.removeEventListener(t,i)}}});let ue=0;const fe={COMPUTE:"__computeEffects",REFLECT:"__reflectEffects",NOTIFY:"__notifyEffects",PROPAGATE:"__propagateEffects",OBSERVE:"__observeEffects",READ_ONLY:"__readOnly"},_e=/[A-Z]/;function me(e,t){let i=e[t];if(i){if(!e.hasOwnProperty(t)){i=e[t]=Object.create(e[t]);for(let e in i){let t=i[e],n=i[e]=Array(t.length);for(let e=0;e<t.length;e++)n[e]=t[e]}}}else i=e[t]={};return i}function ye(e,t,i,n,r,s){if(t){let o=!1,a=ue++;for(let l in i)ge(e,t,a,l,i,n,r,s)&&(o=!0);return o}return!1}function ge(e,t,i,n,r,s,o,a){let l=!1,h=t[o?M(n):n];if(h)for(let t,p=0,c=h.length;p<c&&(t=h[p]);p++)t.info&&t.info.lastRun===i||o&&!be(n,t.trigger)||(t.info&&(t.info.lastRun=i),t.fn(e,n,r,s,t.info,o,a),l=!0);return l}function be(e,t){if(t){let i=t.name;return i==e||!(!t.structured||!L(i,e))||!(!t.wildcard||!D(i,e))}return!0}function ve(e,t,i,n,r){let s="string"==typeof r.method?e[r.method]:r.method,o=r.property;s?s.call(e,e.__data[o],n[o]):r.dynamicFn||console.warn("observer method `"+r.method+"` not defined")}function we(e,t,i){let n=M(t);if(n!==t){return Ce(e,X(n)+"-changed",i[t],t),!0}return!1}function Ce(e,t,i,n){let r={value:i,queueProperty:!0};n&&(r.path=n),R(e).dispatchEvent(new CustomEvent(t,{detail:r}))}function xe(e,t,i,n,r,s){let o=(s?M(t):t)!=t?t:null,a=o?j(e,o):e.__data[t];o&&void 0===a&&(a=i[t]),Ce(e,r.eventName,a,o)}function Pe(e,t,i,n,r){let s=e.__data[t];h&&(s=h(s,r.attrName,"attribute",e)),e._propertyToAttribute(t,r.attrName,s)}function Se(e,t,i,n,r){let s=Ie(e,t,i,n,r),o=r.methodInfo;e.__dataHasAccessor&&e.__dataHasAccessor[o]?e._setPendingProperty(o,s,!0):e[o]=s}function Oe(e,t,i,n,r,s,o){i.bindings=i.bindings||[];let a={kind:n,target:r,parts:s,literal:o,isCompound:1!==s.length};if(i.bindings.push(a),function(e){return Boolean(e.target)&&"attribute"!=e.kind&&"text"!=e.kind&&!e.isCompound&&"{"===e.parts[0].mode}(a)){let{event:e,negate:t}=a.parts[0];a.listenerEvent=e||X(r)+"-changed",a.listenerNegate=t}let l=t.nodeInfoList.length;for(let i=0;i<a.parts.length;i++){let n=a.parts[i];n.compoundIndex=i,Ee(e,t,a,n,l)}}function Ee(e,t,i,n,r){if(!n.literal)if("attribute"===i.kind&&"-"===i.target[0])console.warn("Cannot set attribute "+i.target+' because "-" is not a valid attribute starting character');else{let s=n.dependencies,o={index:r,binding:i,part:n,evaluator:e};for(let i=0;i<s.length;i++){let n=s[i];"string"==typeof n&&((n=De(n)).wildcard=!0),e._addTemplatePropertyEffect(t,n.rootProperty,{fn:Te,info:o,trigger:n})}}}function Te(e,t,i,n,r,s,o){let a=o[r.index],l=r.binding,p=r.part;if(s&&p.source&&t.length>p.source.length&&"property"==l.kind&&!l.isCompound&&a.__isPropertyEffectsClient&&a.__dataHasAccessor&&a.__dataHasAccessor[l.target]){let n=i[t];t=F(p.source,l.target,t),a._setPendingPropertyOrPath(t,n,!1,!0)&&e._enqueueClient(a)}else{!function(e,t,i,n,r){r=function(e,t,i,n){if(i.isCompound){let r=e.__dataCompoundStorage[i.target];r[n.compoundIndex]=t,t=r.join("")}return"attribute"!==i.kind&&("textContent"!==i.target&&("value"!==i.target||"input"!==e.localName&&"textarea"!==e.localName)||(t=null==t?"":t)),t}(t,r,i,n),h&&(r=h(r,i.target,i.kind,t));if("attribute"==i.kind)e._valueToNodeAttribute(t,r,i.target);else{let n=i.target;t.__isPropertyEffectsClient&&t.__dataHasAccessor&&t.__dataHasAccessor[n]?t[fe.READ_ONLY]&&t[fe.READ_ONLY][n]||t._setPendingProperty(n,r)&&e._enqueueClient(t):e._setUnmanagedPropertyToNode(t,n,r)}}(e,a,l,p,r.evaluator._evaluateBinding(e,p,t,i,n,s))}}function Ae(e,t){if(t.isCompound){let i=e.__dataCompoundStorage||(e.__dataCompoundStorage={}),n=t.parts,r=new Array(n.length);for(let e=0;e<n.length;e++)r[e]=n[e].literal;let s=t.target;i[s]=r,t.literal&&"property"==t.kind&&("className"===s&&(e=R(e)),e[s]=t.literal)}}function Ne(e,t,i){if(i.listenerEvent){let n=i.parts[0];e.addEventListener(i.listenerEvent,function(e){!function(e,t,i,n,r){let s,o=e.detail,a=o&&o.path;a?(n=F(i,n,a),s=o&&o.value):s=e.currentTarget[i],s=r?!s:s,t[fe.READ_ONLY]&&t[fe.READ_ONLY][n]||!t._setPendingPropertyOrPath(n,s,!0,Boolean(a))||o&&o.queueProperty||t._invalidateProperties()}(e,t,i.target,n.source,n.negate)})}}function ke(e,t,i,n,r,s){s=t.static||s&&("object"!=typeof s||s[t.methodName]);let o={methodName:t.methodName,args:t.args,methodInfo:r,dynamicFn:s};for(let r,s=0;s<t.args.length&&(r=t.args[s]);s++)r.literal||e._addPropertyEffect(r.rootProperty,i,{fn:n,info:o,trigger:r});s&&e._addPropertyEffect(t.methodName,i,{fn:n,info:o})}function Ie(e,t,i,n,r){let s=e._methodHost||e,o=s[r.methodName];if(o){let n=e._marshalArgs(r.args,t,i);return o.apply(s,n)}r.dynamicFn||console.warn("method `"+r.methodName+"` not defined")}const Re=[],ze=new RegExp("(\\[\\[|{{)\\s*(?:(!)\\s*)?((?:[a-zA-Z_$][\\w.:$\\-*]*)\\s*(?:\\(\\s*(?:(?:(?:((?:[a-zA-Z_$][\\w.:$\\-*]*)|(?:[-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)|(?:(?:'(?:[^'\\\\]|\\\\.)*')|(?:\"(?:[^\"\\\\]|\\\\.)*\")))\\s*)(?:,\\s*(?:((?:[a-zA-Z_$][\\w.:$\\-*]*)|(?:[-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)|(?:(?:'(?:[^'\\\\]|\\\\.)*')|(?:\"(?:[^\"\\\\]|\\\\.)*\")))\\s*))*)?)\\)\\s*)?)(?:]]|}})","g");function Me(e){let t="";for(let i=0;i<e.length;i++){t+=e[i].literal||""}return t}function Le(e){let t=e.match(/([^\s]+?)\(([\s\S]*)\)/);if(t){let e={methodName:t[1],static:!0,args:Re};if(t[2].trim()){return function(e,t){return t.args=e.map(function(e){let i=De(e);return i.literal||(t.static=!1),i},this),t}(t[2].replace(/\\,/g,"&comma;").split(","),e)}return e}return null}function De(e){let t=e.trim().replace(/&comma;/g,",").replace(/\\(.)/g,"$1"),i={name:t,value:"",literal:!1},n=t[0];switch("-"===n&&(n=t[1]),n>="0"&&n<="9"&&(n="#"),n){case"'":case'"':i.value=t.slice(1,-1),i.literal=!0;break;case"#":i.value=Number(t),i.literal=!0}return i.literal||(i.rootProperty=M(t),i.structured=z(t),i.structured&&(i.wildcard=".*"==t.slice(-2),i.wildcard&&(i.name=t.slice(0,-2)))),i}function Fe(e,t,i){let n=j(e,i);return void 0===n&&(n=t[i]),n}function Be(e,t,i,n){e.notifyPath(i+".splices",{indexSplices:n}),e.notifyPath(i+".length",t.length)}function He(e,t,i,n,r,s){Be(e,t,i,[{index:n,addedCount:r,removed:s,object:t,type:"splice"}])}const je=y(e=>{const t=de(se(e));return class extends t{constructor(){super(),this.__isPropertyEffectsClient=!0,this.__dataCounter=0,this.__dataClientsReady,this.__dataPendingClients,this.__dataToNotify,this.__dataLinkedPaths,this.__dataHasPaths,this.__dataCompoundStorage,this.__dataHost,this.__dataTemp,this.__dataClientsInitialized,this.__data,this.__dataPending,this.__dataOld,this.__computeEffects,this.__reflectEffects,this.__notifyEffects,this.__propagateEffects,this.__observeEffects,this.__readOnly,this.__templateInfo}get PROPERTY_EFFECT_TYPES(){return fe}_initializeProperties(){super._initializeProperties(),$e.registerHost(this),this.__dataClientsReady=!1,this.__dataPendingClients=null,this.__dataToNotify=null,this.__dataLinkedPaths=null,this.__dataHasPaths=!1,this.__dataCompoundStorage=this.__dataCompoundStorage||null,this.__dataHost=this.__dataHost||null,this.__dataTemp={},this.__dataClientsInitialized=!1}_initializeProtoProperties(e){this.__data=Object.create(e),this.__dataPending=Object.create(e),this.__dataOld={}}_initializeInstanceProperties(e){let t=this[fe.READ_ONLY];for(let i in e)t&&t[i]||(this.__dataPending=this.__dataPending||{},this.__dataOld=this.__dataOld||{},this.__data[i]=this.__dataPending[i]=e[i])}_addPropertyEffect(e,t,i){this._createPropertyAccessor(e,t==fe.READ_ONLY);let n=me(this,t)[e];n||(n=this[t][e]=[]),n.push(i)}_removePropertyEffect(e,t,i){let n=me(this,t)[e],r=n.indexOf(i);r>=0&&n.splice(r,1)}_hasPropertyEffect(e,t){let i=this[t];return Boolean(i&&i[e])}_hasReadOnlyEffect(e){return this._hasPropertyEffect(e,fe.READ_ONLY)}_hasNotifyEffect(e){return this._hasPropertyEffect(e,fe.NOTIFY)}_hasReflectEffect(e){return this._hasPropertyEffect(e,fe.REFLECT)}_hasComputedEffect(e){return this._hasPropertyEffect(e,fe.COMPUTE)}_setPendingPropertyOrPath(e,t,i,n){if(n||M(Array.isArray(e)?e[0]:e)!==e){if(!n){let i=j(this,e);if(!(e=$(this,e,t))||!super._shouldPropertyChange(e,t,i))return!1}if(this.__dataHasPaths=!0,this._setPendingProperty(e,t,i))return function(e,t,i){let n=e.__dataLinkedPaths;if(n){let r;for(let s in n){let o=n[s];D(s,t)?(r=F(s,o,t),e._setPendingPropertyOrPath(r,i,!0,!0)):D(o,t)&&(r=F(o,s,t),e._setPendingPropertyOrPath(r,i,!0,!0))}}}(this,e,t),!0}else{if(this.__dataHasAccessor&&this.__dataHasAccessor[e])return this._setPendingProperty(e,t,i);this[e]=t}return!1}_setUnmanagedPropertyToNode(e,t,i){i===e[t]&&"object"!=typeof i||("className"===t&&(e=R(e)),e[t]=i)}_setPendingProperty(e,t,i){let n=this.__dataHasPaths&&z(e),r=n?this.__dataTemp:this.__data;return!!this._shouldPropertyChange(e,t,r[e])&&(this.__dataPending||(this.__dataPending={},this.__dataOld={}),e in this.__dataOld||(this.__dataOld[e]=this.__data[e]),n?this.__dataTemp[e]=t:this.__data[e]=t,this.__dataPending[e]=t,(n||this[fe.NOTIFY]&&this[fe.NOTIFY][e])&&(this.__dataToNotify=this.__dataToNotify||{},this.__dataToNotify[e]=i),!0)}_setProperty(e,t){this._setPendingProperty(e,t,!0)&&this._invalidateProperties()}_invalidateProperties(){this.__dataReady&&this._flushProperties()}_enqueueClient(e){this.__dataPendingClients=this.__dataPendingClients||[],e!==this&&this.__dataPendingClients.push(e)}_flushProperties(){this.__dataCounter++,super._flushProperties(),this.__dataCounter--}_flushClients(){this.__dataClientsReady?this.__enableOrFlushClients():(this.__dataClientsReady=!0,this._readyClients(),this.__dataReady=!0)}__enableOrFlushClients(){let e=this.__dataPendingClients;if(e){this.__dataPendingClients=null;for(let t=0;t<e.length;t++){let i=e[t];i.__dataEnabled?i.__dataPending&&i._flushProperties():i._enableProperties()}}}_readyClients(){this.__enableOrFlushClients()}setProperties(e,t){for(let i in e)!t&&this[fe.READ_ONLY]&&this[fe.READ_ONLY][i]||this._setPendingPropertyOrPath(i,e[i],!0);this._invalidateProperties()}ready(){this._flushProperties(),this.__dataClientsReady||this._flushClients(),this.__dataPending&&this._flushProperties()}_propertiesChanged(e,t,i){let n=this.__dataHasPaths;this.__dataHasPaths=!1,function(e,t,i,n){let r=e[fe.COMPUTE];if(r){let s=t;for(;ye(e,r,s,i,n);)Object.assign(i,e.__dataOld),Object.assign(t,e.__dataPending),s=e.__dataPending,e.__dataPending=null}}(this,t,i,n);let r=this.__dataToNotify;this.__dataToNotify=null,this._propagatePropertyChanges(t,i,n),this._flushClients(),ye(this,this[fe.REFLECT],t,i,n),ye(this,this[fe.OBSERVE],t,i,n),r&&function(e,t,i,n,r){let s,o,a=e[fe.NOTIFY],l=ue++;for(let o in t)t[o]&&(a&&ge(e,a,l,o,i,n,r)?s=!0:r&&we(e,o,i)&&(s=!0));s&&(o=e.__dataHost)&&o._invalidateProperties&&o._invalidateProperties()}(this,r,t,i,n),1==this.__dataCounter&&(this.__dataTemp={})}_propagatePropertyChanges(e,t,i){this[fe.PROPAGATE]&&ye(this,this[fe.PROPAGATE],e,t,i);let n=this.__templateInfo;for(;n;)ye(this,n.propertyEffects,e,t,i,n.nodeList),n=n.nextTemplateInfo}linkPaths(e,t){e=B(e),t=B(t),this.__dataLinkedPaths=this.__dataLinkedPaths||{},this.__dataLinkedPaths[e]=t}unlinkPaths(e){e=B(e),this.__dataLinkedPaths&&delete this.__dataLinkedPaths[e]}notifySplices(e,t){let i={path:""};Be(this,j(this,e,i),i.path,t)}get(e,t){return j(t||this,e)}set(e,t,i){i?$(i,e,t):this[fe.READ_ONLY]&&this[fe.READ_ONLY][e]||this._setPendingPropertyOrPath(e,t,!0)&&this._invalidateProperties()}push(e,...t){let i={path:""},n=j(this,e,i),r=n.length,s=n.push(...t);return t.length&&He(this,n,i.path,r,t.length,[]),s}pop(e){let t={path:""},i=j(this,e,t),n=Boolean(i.length),r=i.pop();return n&&He(this,i,t.path,i.length,0,[r]),r}splice(e,t,i,...n){let r,s={path:""},o=j(this,e,s);return t<0?t=o.length-Math.floor(-t):t&&(t=Math.floor(t)),r=2===arguments.length?o.splice(t):o.splice(t,i,...n),(n.length||r.length)&&He(this,o,s.path,t,n.length,r),r}shift(e){let t={path:""},i=j(this,e,t),n=Boolean(i.length),r=i.shift();return n&&He(this,i,t.path,0,0,[r]),r}unshift(e,...t){let i={path:""},n=j(this,e,i),r=n.unshift(...t);return t.length&&He(this,n,i.path,0,t.length,[]),r}notifyPath(e,t){let i;if(1==arguments.length){let n={path:""};t=j(this,e,n),i=n.path}else i=Array.isArray(e)?B(e):e;this._setPendingPropertyOrPath(i,t,!0,!0)&&this._invalidateProperties()}_createReadOnlyProperty(e,t){var i;this._addPropertyEffect(e,fe.READ_ONLY),t&&(this["_set"+(i=e,i[0].toUpperCase()+i.substring(1))]=function(t){this._setProperty(e,t)})}_createPropertyObserver(e,t,i){let n={property:e,method:t,dynamicFn:Boolean(i)};this._addPropertyEffect(e,fe.OBSERVE,{fn:ve,info:n,trigger:{name:e}}),i&&this._addPropertyEffect(t,fe.OBSERVE,{fn:ve,info:n,trigger:{name:t}})}_createMethodObserver(e,t){let i=Le(e);if(!i)throw new Error("Malformed observer expression '"+e+"'");ke(this,i,fe.OBSERVE,Ie,null,t)}_createNotifyingProperty(e){this._addPropertyEffect(e,fe.NOTIFY,{fn:xe,info:{eventName:X(e)+"-changed",property:e}})}_createReflectedProperty(e){let t=this.constructor.attributeNameForProperty(e);"-"===t[0]?console.warn("Property "+e+" cannot be reflected to attribute "+t+' because "-" is not a valid starting attribute name. Use a lowercase first letter for the property instead.'):this._addPropertyEffect(e,fe.REFLECT,{fn:Pe,info:{attrName:t}})}_createComputedProperty(e,t,i){let n=Le(t);if(!n)throw new Error("Malformed computed expression '"+t+"'");ke(this,n,fe.COMPUTE,Se,e,i)}_marshalArgs(e,t,i){const n=this.__data,r=[];for(let s=0,o=e.length;s<o;s++){let{name:o,structured:a,wildcard:l,value:h,literal:p}=e[s];if(!p)if(l){const e=D(o,t),r=Fe(n,i,e?t:o);h={path:e?t:o,value:r,base:e?j(n,o):r}}else h=a?Fe(n,i,o):n[o];r[s]=h}return r}static addPropertyEffect(e,t,i){this.prototype._addPropertyEffect(e,t,i)}static createPropertyObserver(e,t,i){this.prototype._createPropertyObserver(e,t,i)}static createMethodObserver(e,t){this.prototype._createMethodObserver(e,t)}static createNotifyingProperty(e){this.prototype._createNotifyingProperty(e)}static createReadOnlyProperty(e,t){this.prototype._createReadOnlyProperty(e,t)}static createReflectedProperty(e){this.prototype._createReflectedProperty(e)}static createComputedProperty(e,t,i){this.prototype._createComputedProperty(e,t,i)}static bindTemplate(e){return this.prototype._bindTemplate(e)}_bindTemplate(e,t){let i=this.constructor._parseTemplate(e),n=this.__templateInfo==i;if(!n)for(let e in i.propertyEffects)this._createPropertyAccessor(e);if(t&&((i=Object.create(i)).wasPreBound=n,!n&&this.__templateInfo)){let e=this.__templateInfoLast||this.__templateInfo;return this.__templateInfoLast=e.nextTemplateInfo=i,i.previousTemplateInfo=e,i}return this.__templateInfo=i}static _addTemplatePropertyEffect(e,t,i){(e.hostProps=e.hostProps||{})[t]=!0;let n=e.propertyEffects=e.propertyEffects||{};(n[t]=n[t]||[]).push(i)}_stampTemplate(e){$e.beginHosting(this);let t=super._stampTemplate(e);$e.endHosting(this);let i=this._bindTemplate(e,!0);if(i.nodeList=t.nodeList,!i.wasPreBound){let e=i.childNodes=[];for(let i=t.firstChild;i;i=i.nextSibling)e.push(i)}return t.templateInfo=i,function(e,t){let{nodeList:i,nodeInfoList:n}=t;if(n.length)for(let t=0;t<n.length;t++){let r=n[t],s=i[t],o=r.bindings;if(o)for(let t=0;t<o.length;t++){let i=o[t];Ae(s,i),Ne(s,e,i)}s.__dataHost=e}}(this,i),this.__dataReady&&ye(this,i.propertyEffects,this.__data,null,!1,i.nodeList),t}_removeBoundDom(e){let t=e.templateInfo;t.previousTemplateInfo&&(t.previousTemplateInfo.nextTemplateInfo=t.nextTemplateInfo),t.nextTemplateInfo&&(t.nextTemplateInfo.previousTemplateInfo=t.previousTemplateInfo),this.__templateInfoLast==t&&(this.__templateInfoLast=t.previousTemplateInfo),t.previousTemplateInfo=t.nextTemplateInfo=null;let i=t.childNodes;for(let e=0;e<i.length;e++){let t=i[e];t.parentNode.removeChild(t)}}static _parseTemplateNode(e,i,n){let r=t._parseTemplateNode.call(this,e,i,n);if(e.nodeType===Node.TEXT_NODE){let t=this._parseBindings(e.textContent,i);t&&(e.textContent=Me(t)||" ",Oe(this,i,n,"text","textContent",t),r=!0)}return r}static _parseTemplateNodeAttribute(e,i,n,r,s){let o=this._parseBindings(s,i);if(o){let t=r,s="property";_e.test(r)?s="attribute":"$"==r[r.length-1]&&(r=r.slice(0,-1),s="attribute");let a=Me(o);return a&&"attribute"==s&&("class"==r&&e.hasAttribute("class")&&(a+=" "+e.getAttribute(r)),e.setAttribute(r,a)),"input"===e.localName&&"value"===t&&e.setAttribute(t,""),e.removeAttribute(t),"property"===s&&(r=V(r)),Oe(this,i,n,s,r,o,a),!0}return t._parseTemplateNodeAttribute.call(this,e,i,n,r,s)}static _parseTemplateNestedTemplate(e,i,n){let r=t._parseTemplateNestedTemplate.call(this,e,i,n),s=n.templateInfo.hostProps;for(let e in s)Oe(this,i,n,"property","_host_"+e,[{mode:"{",source:e,dependencies:[e]}]);return r}static _parseBindings(e,t){let i,n=[],r=0;for(;null!==(i=ze.exec(e));){i.index>r&&n.push({literal:e.slice(r,i.index)});let s=i[1][0],o=Boolean(i[2]),a=i[3].trim(),l=!1,h="",p=-1;"{"==s&&(p=a.indexOf("::"))>0&&(h=a.substring(p+2),a=a.substring(0,p),l=!0);let c=Le(a),d=[];if(c){let{args:e,methodName:i}=c;for(let t=0;t<e.length;t++){let i=e[t];i.literal||d.push(i)}let n=t.dynamicFns;(n&&n[i]||c.static)&&(d.push(i),c.dynamicFn=!0)}else d.push(a);n.push({source:a,mode:s,negate:o,customEvent:l,signature:c,dependencies:d,event:h}),r=ze.lastIndex}if(r&&r<e.length){let t=e.substring(r);t&&n.push({literal:t})}return n.length?n:null}static _evaluateBinding(e,t,i,n,r,s){let o;return o=t.signature?Ie(e,i,n,0,t.signature):i!=t.source?j(e,t.source):s&&z(i)?j(e,i):e.__data[i],t.negate&&(o=!o),o}}});const $e=new class{constructor(){this.stack=[]}registerHost(e){this.stack.length&&this.stack[this.stack.length-1]._enqueueClient(e)}beginHosting(e){this.stack.push(e)}endHosting(e){let t=this.stack.length;t&&this.stack[t-1]==e&&this.stack.pop()}};const qe=y(e=>{const t=ie(e);function i(e){const t=Object.getPrototypeOf(e);return t.prototype instanceof r?t:null}function n(e){if(!e.hasOwnProperty(JSCompiler_renameProperty("__ownProperties",e))){let t=null;if(e.hasOwnProperty(JSCompiler_renameProperty("properties",e))){const i=e.properties;i&&(t=function(e){const t={};for(let i in e){const n=e[i];t[i]="function"==typeof n?{type:n}:n}return t}(i))}e.__ownProperties=t}return e.__ownProperties}class r extends t{static get observedAttributes(){if(!this.hasOwnProperty("__observedAttributes")){this.prototype;const e=this._properties;this.__observedAttributes=e?Object.keys(e).map(e=>this.attributeNameForProperty(e)):[]}return this.__observedAttributes}static finalize(){if(!this.hasOwnProperty(JSCompiler_renameProperty("__finalized",this))){const e=i(this);e&&e.finalize(),this.__finalized=!0,this._finalizeClass()}}static _finalizeClass(){const e=n(this);e&&this.createProperties(e)}static get _properties(){if(!this.hasOwnProperty(JSCompiler_renameProperty("__properties",this))){const e=i(this);this.__properties=Object.assign({},e&&e._properties,n(this))}return this.__properties}static typeForProperty(e){const t=this._properties[e];return t&&t.type}_initializeProperties(){this.constructor.finalize(),super._initializeProperties()}connectedCallback(){super.connectedCallback&&super.connectedCallback(),this._enableProperties()}disconnectedCallback(){super.disconnectedCallback&&super.disconnectedCallback()}}return r}),Ye="3.3.0",Ue=window.ShadyCSS&&window.ShadyCSS.cssBuild,Ve=y(e=>{const t=qe(je(e));function i(e,t,i,n){if(!Ue){const r=t.content.querySelectorAll("style"),s=N(t),o=function(e){let t=O(e);return t?k(t):[]}(i),a=t.content.firstElementChild;for(let i=0;i<o.length;i++){let r=o[i];r.textContent=e._processStyleText(r.textContent,n),t.content.insertBefore(r,a)}let l=0;for(let t=0;t<s.length;t++){let i=s[t],o=r[l];o!==i?(i=i.cloneNode(!0),o.parentNode.insertBefore(i,o)):l++,i.textContent=e._processStyleText(i.textContent,n)}}window.ShadyCSS&&window.ShadyCSS.prepareTemplate(t,i)}return class extends t{static get polymerElementVersion(){return Ye}static _finalizeClass(){t._finalizeClass.call(this);const e=((i=this).hasOwnProperty(JSCompiler_renameProperty("__ownObservers",i))||(i.__ownObservers=i.hasOwnProperty(JSCompiler_renameProperty("observers",i))?i.observers:null),i.__ownObservers);var i;e&&this.createObservers(e,this._properties),this._prepareTemplate()}static _prepareTemplate(){let e=this.template;e&&("string"==typeof e?(console.error("template getter must return HTMLTemplateElement"),e=null):u||(e=e.cloneNode(!0))),this.prototype._template=e}static createProperties(e){for(let s in e)t=this.prototype,i=s,n=e[s],r=e,n.computed&&(n.readOnly=!0),n.computed&&(t._hasReadOnlyEffect(i)?console.warn(`Cannot redefine computed property '${i}'.`):t._createComputedProperty(i,n.computed,r)),n.readOnly&&!t._hasReadOnlyEffect(i)?t._createReadOnlyProperty(i,!n.computed):!1===n.readOnly&&t._hasReadOnlyEffect(i)&&console.warn(`Cannot make readOnly property '${i}' non-readOnly.`),n.reflectToAttribute&&!t._hasReflectEffect(i)?t._createReflectedProperty(i):!1===n.reflectToAttribute&&t._hasReflectEffect(i)&&console.warn(`Cannot make reflected property '${i}' non-reflected.`),n.notify&&!t._hasNotifyEffect(i)?t._createNotifyingProperty(i):!1===n.notify&&t._hasNotifyEffect(i)&&console.warn(`Cannot make notify property '${i}' non-notify.`),n.observer&&t._createPropertyObserver(i,n.observer,r[n.observer]),t._addPropertyToAttributeMap(i);var t,i,n,r}static createObservers(e,t){const i=this.prototype;for(let n=0;n<e.length;n++)i._createMethodObserver(e[n],t)}static get template(){return this.hasOwnProperty(JSCompiler_renameProperty("_template",this))||(this._template=this.prototype.hasOwnProperty(JSCompiler_renameProperty("_template",this.prototype))?this.prototype._template:function(e){let t=null;if(e&&(!c||d)&&(t=C.import(e,"template"),c&&!t))throw new Error(`strictTemplatePolicy: expecting dom-module or null template for ${e}`);return t}(this.is)||Object.getPrototypeOf(this.prototype).constructor.template),this._template}static set template(e){this._template=e}static get importPath(){if(!this.hasOwnProperty(JSCompiler_renameProperty("_importPath",this))){const e=this.importMeta;if(e)this._importPath=o(e.url);else{const e=C.import(this.is);this._importPath=e&&e.assetpath||Object.getPrototypeOf(this.prototype).constructor.importPath}}return this._importPath}constructor(){super(),this._template,this._importPath,this.rootPath,this.importPath,this.root,this.$}_initializeProperties(){this.constructor.finalize(),this.constructor._finalizeTemplate(this.localName),super._initializeProperties(),this.rootPath=l,this.importPath=this.constructor.importPath;let e=function(e){if(!e.hasOwnProperty(JSCompiler_renameProperty("__propertyDefaults",e))){e.__propertyDefaults=null;let t=e._properties;for(let i in t){let n=t[i];"value"in n&&(e.__propertyDefaults=e.__propertyDefaults||{},e.__propertyDefaults[i]=n)}}return e.__propertyDefaults}(this.constructor);if(e)for(let t in e){let i=e[t];if(!this.hasOwnProperty(t)){let e="function"==typeof i.value?i.value.call(this):i.value;this._hasAccessor(t)?this._setPendingProperty(t,e,!0):this[t]=e}}}static _processStyleText(e,t){return s(e,t)}static _finalizeTemplate(e){const t=this.prototype._template;if(t&&!t.__polymerFinalized){t.__polymerFinalized=!0;const n=this.importPath;i(this,t,e,n?r(n):""),this.prototype._bindTemplate(t)}}connectedCallback(){window.ShadyCSS&&this._template&&window.ShadyCSS.styleElement(this),super.connectedCallback()}ready(){this._template&&(this.root=this._stampTemplate(this._template),this.$=this.root.$),super.ready()}_readyClients(){this._template&&(this.root=this._attachDom(this.root)),super._readyClients()}_attachDom(e){const t=R(this);if(t.attachShadow)return e?(t.shadowRoot||(t.attachShadow({mode:"open",shadyUpgradeFragment:e}),t.shadowRoot.appendChild(e)),f&&window.ShadyDOM&&ShadyDOM.flushInitial(t.shadowRoot),t.shadowRoot):null;throw new Error("ShadowDOM not available. PolymerElement can create dom as children instead of in ShadowDOM by setting `this.root = this;` before `ready`.")}updateStyles(e){window.ShadyCSS&&window.ShadyCSS.styleSubtree(this,e)}resolveUrl(e,t){return!t&&this.importPath&&(t=r(this.importPath)),r(e,t)}static _parseTemplateContent(e,i,n){return i.dynamicFns=i.dynamicFns||this._properties,t._parseTemplateContent.call(this,e,i,n)}static _addTemplatePropertyEffect(e,i,n){return!u||i in this._properties||console.warn(`Property '${i}' used in template but not declared in 'properties'; `+"attribute will not be observed."),t._addTemplatePropertyEffect.call(this,e,i,n)}}});class Xe{constructor(e){this.value=e.toString()}toString(){return this.value}}function Je(e){if(e instanceof HTMLTemplateElement)return e.innerHTML;if(e instanceof Xe)return function(e){if(e instanceof Xe)return e.value;throw new Error(`non-literal value passed to Polymer's htmlLiteral function: ${e}`)}(e);throw new Error(`non-template value passed to Polymer's html function: ${e}`)}const We=function(e,...t){const i=document.createElement("template");return i.innerHTML=t.reduce((t,i,n)=>t+Je(i)+e[n+1],e[0]),i},Ze=Ve(HTMLElement),Ke=!(window.ShadyDOM&&window.ShadyDOM.inUse);let Ge,Qe;function et(e){Ge=(!e||!e.shimcssproperties)&&(Ke||Boolean(!navigator.userAgent.match(/AppleWebKit\/601|Edge\/15/)&&window.CSS&&CSS.supports&&CSS.supports("box-shadow","0 0 0 var(--foo)")))}window.ShadyCSS&&void 0!==window.ShadyCSS.cssBuild&&(Qe=window.ShadyCSS.cssBuild);const tt=Boolean(window.ShadyCSS&&window.ShadyCSS.disableRuntime);window.ShadyCSS&&void 0!==window.ShadyCSS.nativeCss?Ge=window.ShadyCSS.nativeCss:window.ShadyCSS?(et(window.ShadyCSS),window.ShadyCSS=void 0):et(window.WebComponents&&window.WebComponents.flags);const it=Ge;class nt{constructor(){this.start=0,this.end=0,this.previous=null,this.parent=null,this.rules=null,this.parsedCssText="",this.cssText="",this.atRule=!1,this.type=0,this.keyframesName="",this.selector="",this.parsedSelector=""}}function rt(e){return function e(t,i){let n=i.substring(t.start,t.end-1);t.parsedCssText=t.cssText=n.trim();if(t.parent){let e=t.previous?t.previous.end:t.parent.start;n=(n=(n=function(e){return e.replace(/\\([0-9a-f]{1,6})\s/gi,function(){let e=arguments[1],t=6-e.length;for(;t--;)e="0"+e;return"\\"+e})}(n=i.substring(e,t.start-1))).replace(ht.multipleSpaces," ")).substring(n.lastIndexOf(";")+1);let r=t.parsedSelector=t.selector=n.trim();t.atRule=0===r.indexOf(dt),t.atRule?0===r.indexOf(ct)?t.type=ot.MEDIA_RULE:r.match(ht.keyframesRule)&&(t.type=ot.KEYFRAMES_RULE,t.keyframesName=t.selector.split(ht.multipleSpaces).pop()):0===r.indexOf(pt)?t.type=ot.MIXIN_RULE:t.type=ot.STYLE_RULE}let r=t.rules;if(r)for(let t,n=0,s=r.length;n<s&&(t=r[n]);n++)e(t,i);return t}(function(e){let t=new nt;t.start=0,t.end=e.length;let i=t;for(let n=0,r=e.length;n<r;n++)if(e[n]===at){i.rules||(i.rules=[]);let e=i,t=e.rules[e.rules.length-1]||null;(i=new nt).start=n+1,i.parent=e,i.previous=t,e.rules.push(i)}else e[n]===lt&&(i.end=n+1,i=i.parent||t);return t}(e=e.replace(ht.comments,"").replace(ht.port,"")),e)}function st(e,t,i=""){let n="";if(e.cssText||e.rules){let i=e.rules;if(i&&!function(e){let t=e[0];return Boolean(t)&&Boolean(t.selector)&&0===t.selector.indexOf(pt)}(i))for(let e,r=0,s=i.length;r<s&&(e=i[r]);r++)n=st(e,t,n);else(n=(n=t?e.cssText:function(e){return function(e){return e.replace(ht.mixinApply,"").replace(ht.varApply,"")}(e=function(e){return e.replace(ht.customProp,"").replace(ht.mixinProp,"")}(e))}(e.cssText)).trim())&&(n="  "+n+"\n")}return n&&(e.selector&&(i+=e.selector+" "+at+"\n"),i+=n,e.selector&&(i+=lt+"\n\n")),i}const ot={STYLE_RULE:1,KEYFRAMES_RULE:7,MEDIA_RULE:4,MIXIN_RULE:1e3},at="{",lt="}",ht={comments:/\/\*[^*]*\*+([^\/*][^*]*\*+)*\//gim,port:/@import[^;]*;/gim,customProp:/(?:^[^;\-\s}]+)?--[^;{}]*?:[^{};]*?(?:[;\n]|$)/gim,mixinProp:/(?:^[^;\-\s}]+)?--[^;{}]*?:[^{};]*?{[^}]*?}(?:[;\n]|$)?/gim,mixinApply:/@apply\s*\(?[^);]*\)?\s*(?:[;\n]|$)?/gim,varApply:/[^;:]*?:[^;]*?var\([^;]*\)(?:[;\n]|$)?/gim,keyframesRule:/^@[^\s]*keyframes/,multipleSpaces:/\s+/g},pt="--",ct="@media",dt="@",ut=/(?:^|[;\s{]\s*)(--[\w-]*?)\s*:\s*(?:((?:'(?:\\'|.)*?'|"(?:\\"|.)*?"|\([^)]*?\)|[^};{])+)|\{([^}]*)\}(?:(?=[;\s}])|$))/gi,ft=/(?:^|\W+)@apply\s*\(?([^);\n]*)\)?/gi,_t=/@media\s(.*)/,mt=new Set,yt="shady-unscoped";function gt(e){const t=e.textContent;if(!mt.has(t)){mt.add(t);const i=e.cloneNode(!0);document.head.appendChild(i)}}function bt(e){return e.hasAttribute(yt)}function vt(e,t){return e?("string"==typeof e&&(e=rt(e)),t&&Ct(e,t),st(e,it)):""}function wt(e){return!e.__cssRules&&e.textContent&&(e.__cssRules=rt(e.textContent)),e.__cssRules||null}function Ct(e,t,i,n){if(!e)return;let r=!1,s=e.type;if(n&&s===ot.MEDIA_RULE){let t=e.selector.match(_t);t&&(window.matchMedia(t[1]).matches||(r=!0))}s===ot.STYLE_RULE?t(e):i&&s===ot.KEYFRAMES_RULE?i(e):s===ot.MIXIN_RULE&&(r=!0);let o=e.rules;if(o&&!r)for(let e,r=0,s=o.length;r<s&&(e=o[r]);r++)Ct(e,t,i,n)}window.ShadyDOM&&window.ShadyDOM.wrap;const xt="css-build";function Pt(e){if(void 0!==Qe)return Qe;if(void 0===e.__cssBuild){const t=e.getAttribute(xt);if(t)e.__cssBuild=t;else{const t=function(e){const t="template"===e.localName?e.content.firstChild:e.firstChild;if(t instanceof Comment){const e=t.textContent.trim().split(":");if(e[0]===xt)return e[1]}return""}(e);""!==t&&function(e){const t="template"===e.localName?e.content.firstChild:e.firstChild;t.parentNode.removeChild(t)}(e),e.__cssBuild=t}}return e.__cssBuild||""}function St(e){return""!==Pt(e)}function Ot(e,t){for(let i in t)null===i?e.style.removeProperty(i):e.style.setProperty(i,t[i])}function Et(e,t){const i=window.getComputedStyle(e).getPropertyValue(t);return i?i.trim():""}const Tt=/;\s*/m,At=/^\s*(initial)|(inherit)\s*$/,Nt=/\s*!important/,kt="_-_";class It{constructor(){this._map={}}set(e,t){e=e.trim(),this._map[e]={properties:t,dependants:{}}}get(e){return e=e.trim(),this._map[e]||null}}let Rt=null;class zt{constructor(){this._currentElement=null,this._measureElement=null,this._map=new It}detectMixin(e){return function(e){const t=ft.test(e)||ut.test(e);return ft.lastIndex=0,ut.lastIndex=0,t}(e)}gatherStyles(e){const t=function(e){const t=[],i=e.querySelectorAll("style");for(let e=0;e<i.length;e++){const n=i[e];bt(n)?Ke||(gt(n),n.parentNode.removeChild(n)):(t.push(n.textContent),n.parentNode.removeChild(n))}return t.join("").trim()}(e.content);if(t){const i=document.createElement("style");return i.textContent=t,e.content.insertBefore(i,e.content.firstChild),i}return null}transformTemplate(e,t){void 0===e._gatheredStyle&&(e._gatheredStyle=this.gatherStyles(e));const i=e._gatheredStyle;return i?this.transformStyle(i,t):null}transformStyle(e,t=""){let i=wt(e);return this.transformRules(i,t),e.textContent=vt(i),i}transformCustomStyle(e){let t=wt(e);return Ct(t,e=>{":root"===e.selector&&(e.selector="html"),this.transformRule(e)}),e.textContent=vt(t),t}transformRules(e,t){this._currentElement=t,Ct(e,e=>{this.transformRule(e)}),this._currentElement=null}transformRule(e){e.cssText=this.transformCssText(e.parsedCssText,e),":root"===e.selector&&(e.selector=":host > *")}transformCssText(e,t){return e=e.replace(ut,(e,i,n,r)=>this._produceCssProperties(e,i,n,r,t)),this._consumeCssProperties(e,t)}_getInitialValueForProperty(e){return this._measureElement||(this._measureElement=document.createElement("meta"),this._measureElement.setAttribute("apply-shim-measure",""),this._measureElement.style.all="initial",document.head.appendChild(this._measureElement)),window.getComputedStyle(this._measureElement).getPropertyValue(e)}_fallbacksFromPreviousRules(e){let t=e;for(;t.parent;)t=t.parent;const i={};let n=!1;return Ct(t,t=>{(n=n||t===e)||t.selector===e.selector&&Object.assign(i,this._cssTextToMap(t.parsedCssText))}),i}_consumeCssProperties(e,t){let i=null;for(;i=ft.exec(e);){let n=i[0],r=i[1],s=i.index,o=s+n.indexOf("@apply"),a=s+n.length,l=e.slice(0,o),h=e.slice(a),p=t?this._fallbacksFromPreviousRules(t):{};Object.assign(p,this._cssTextToMap(l));let c=this._atApplyToCssProperties(r,p);e=`${l}${c}${h}`,ft.lastIndex=s+c.length}return e}_atApplyToCssProperties(e,t){e=e.replace(Tt,"");let i=[],n=this._map.get(e);if(n||(this._map.set(e,{}),n=this._map.get(e)),n){let r,s,o;this._currentElement&&(n.dependants[this._currentElement]=!0);const a=n.properties;for(r in a)o=t&&t[r],s=[r,": var(",e,kt,r],o&&s.push(",",o.replace(Nt,"")),s.push(")"),Nt.test(a[r])&&s.push(" !important"),i.push(s.join(""))}return i.join("; ")}_replaceInitialOrInherit(e,t){let i=At.exec(t);return i&&(t=i[1]?this._getInitialValueForProperty(e):"apply-shim-inherit"),t}_cssTextToMap(e,t=!1){let i,n,r=e.split(";"),s={};for(let e,o,a=0;a<r.length;a++)(e=r[a])&&(o=e.split(":")).length>1&&(i=o[0].trim(),n=o.slice(1).join(":"),t&&(n=this._replaceInitialOrInherit(i,n)),s[i]=n);return s}_invalidateMixinEntry(e){if(Rt)for(let t in e.dependants)t!==this._currentElement&&Rt(t)}_produceCssProperties(e,t,i,n,r){if(i&&function e(t,i){let n=t.indexOf("var(");if(-1===n)return i(t,"","","");let r=function(e,t){let i=0;for(let n=t,r=e.length;n<r;n++)if("("===e[n])i++;else if(")"===e[n]&&0==--i)return n;return-1}(t,n+3),s=t.substring(n+4,r),o=t.substring(0,n),a=e(t.substring(r+1),i),l=s.indexOf(",");return-1===l?i(o,s.trim(),"",a):i(o,s.substring(0,l).trim(),s.substring(l+1).trim(),a)}(i,(e,t)=>{t&&this._map.get(t)&&(n=`@apply ${t};`)}),!n)return e;let s=this._consumeCssProperties(""+n,r),o=e.slice(0,e.indexOf("--")),a=this._cssTextToMap(s,!0),l=a,h=this._map.get(t),p=h&&h.properties;p?l=Object.assign(Object.create(p),a):this._map.set(t,l);let c,d,u=[],f=!1;for(c in l)void 0===(d=a[c])&&(d="initial"),!p||c in p||(f=!0),u.push(`${t}${kt}${c}: ${d}`);return f&&this._invalidateMixinEntry(h),h&&(h.properties=l),i&&(o=`${e};${o}`),`${o}${u.join("; ")};`}}zt.prototype.detectMixin=zt.prototype.detectMixin,zt.prototype.transformStyle=zt.prototype.transformStyle,zt.prototype.transformCustomStyle=zt.prototype.transformCustomStyle,zt.prototype.transformRules=zt.prototype.transformRules,zt.prototype.transformRule=zt.prototype.transformRule,zt.prototype.transformTemplate=zt.prototype.transformTemplate,zt.prototype._separator=kt,Object.defineProperty(zt.prototype,"invalidCallback",{get:()=>Rt,set(e){Rt=e}});const Mt={},Lt="_applyShimCurrentVersion",Dt="_applyShimNextVersion",Ft="_applyShimValidatingVersion",Bt=Promise.resolve();function Ht(e){let t=Mt[e];t&&function(e){e[Lt]=e[Lt]||0,e[Ft]=e[Ft]||0,e[Dt]=(e[Dt]||0)+1}(t)}function jt(e){return e[Lt]===e[Dt]}let $t,qt=null,Yt=window.HTMLImports&&window.HTMLImports.whenReady||null;function Ut(e){requestAnimationFrame(function(){Yt?Yt(e):(qt||(qt=new Promise(e=>{$t=e}),"complete"===document.readyState?$t():document.addEventListener("readystatechange",()=>{"complete"===document.readyState&&$t()})),qt.then(function(){e&&e()}))})}const Vt="__seenByShadyCSS",Xt="__shadyCSSCachedStyle";let Jt=null,Wt=null;class Zt{constructor(){this.customStyles=[],this.enqueued=!1,Ut(()=>{window.ShadyCSS.flushCustomStyles&&window.ShadyCSS.flushCustomStyles()})}enqueueDocumentValidation(){!this.enqueued&&Wt&&(this.enqueued=!0,Ut(Wt))}addCustomStyle(e){e[Vt]||(e[Vt]=!0,this.customStyles.push(e),this.enqueueDocumentValidation())}getStyleForCustomStyle(e){if(e[Xt])return e[Xt];let t;return t=e.getStyle?e.getStyle():e}processStyles(){const e=this.customStyles;for(let t=0;t<e.length;t++){const i=e[t];if(i[Xt])continue;const n=this.getStyleForCustomStyle(i);if(n){const e=n.__appliedElement||n;Jt&&Jt(e),i[Xt]=e}}return e}}Zt.prototype.addCustomStyle=Zt.prototype.addCustomStyle,Zt.prototype.getStyleForCustomStyle=Zt.prototype.getStyleForCustomStyle,Zt.prototype.processStyles=Zt.prototype.processStyles,Object.defineProperties(Zt.prototype,{transformCallback:{get:()=>Jt,set(e){Jt=e}},validateCallback:{get:()=>Wt,set(e){let t=!1;Wt||(t=!0),Wt=e,t&&this.enqueueDocumentValidation()}}});const Kt=new zt;class Gt{constructor(){this.customStyleInterface=null,Kt.invalidCallback=Ht}ensure(){this.customStyleInterface||window.ShadyCSS.CustomStyleInterface&&(this.customStyleInterface=window.ShadyCSS.CustomStyleInterface,this.customStyleInterface.transformCallback=(e=>{Kt.transformCustomStyle(e)}),this.customStyleInterface.validateCallback=(()=>{requestAnimationFrame(()=>{this.customStyleInterface.enqueued&&this.flushCustomStyles()})}))}prepareTemplate(e,t){if(this.ensure(),St(e))return;Mt[t]=e;let i=Kt.transformTemplate(e,t);e._styleAst=i}flushCustomStyles(){if(this.ensure(),!this.customStyleInterface)return;let e=this.customStyleInterface.processStyles();if(this.customStyleInterface.enqueued){for(let t=0;t<e.length;t++){let i=e[t],n=this.customStyleInterface.getStyleForCustomStyle(i);n&&Kt.transformCustomStyle(n)}this.customStyleInterface.enqueued=!1}}styleSubtree(e,t){if(this.ensure(),t&&Ot(e,t),e.shadowRoot){this.styleElement(e);let t=e.shadowRoot.children||e.shadowRoot.childNodes;for(let e=0;e<t.length;e++)this.styleSubtree(t[e])}else{let t=e.children||e.childNodes;for(let e=0;e<t.length;e++)this.styleSubtree(t[e])}}styleElement(e){this.ensure();let{is:t}=function(e){let t=e.localName,i="",n="";return t?t.indexOf("-")>-1?i=t:(n=t,i=e.getAttribute&&e.getAttribute("is")||""):(i=e.is,n=e.extends),{is:i,typeExtension:n}}(e),i=Mt[t];if((!i||!St(i))&&i&&!jt(i)){(function(e){return!jt(e)&&e[Ft]===e[Dt]})(i)||(this.prepareTemplate(i,t),function(e){e[Ft]=e[Dt],e._validating||(e._validating=!0,Bt.then(function(){e[Lt]=e[Dt],e._validating=!1}))}(i));let n=e.shadowRoot;if(n){let e=n.querySelector("style");e&&(e.__cssRules=i._styleAst,e.textContent=vt(i._styleAst))}}}styleDocument(e){this.ensure(),this.styleSubtree(document.body,e)}}if(!window.ShadyCSS||!window.ShadyCSS.ScopingShim){const e=new Gt;let t=window.ShadyCSS&&window.ShadyCSS.CustomStyleInterface;window.ShadyCSS={prepareTemplate(t,i,n){e.flushCustomStyles(),e.prepareTemplate(t,i)},prepareTemplateStyles(e,t,i){window.ShadyCSS.prepareTemplate(e,t,i)},prepareTemplateDom(e,t){},styleSubtree(t,i){e.flushCustomStyles(),e.styleSubtree(t,i)},styleElement(t){e.flushCustomStyles(),e.styleElement(t)},styleDocument(t){e.flushCustomStyles(),e.styleDocument(t)},getComputedStyleValue:(e,t)=>Et(e,t),flushCustomStyles(){e.flushCustomStyles()},nativeCss:it,nativeShadow:Ke,cssBuild:Qe,disableRuntime:tt},t&&(window.ShadyCSS.CustomStyleInterface=t)}window.ShadyCSS.ApplyShim=Kt;class Qt{constructor(){this._asyncModule=null,this._callback=null,this._timer=null}setConfig(e,t){this._asyncModule=e,this._callback=t,this._timer=this._asyncModule.run(()=>{this._timer=null,ei.delete(this),this._callback()})}cancel(){this.isActive()&&(this._cancelAsync(),ei.delete(this))}_cancelAsync(){this.isActive()&&(this._asyncModule.cancel(this._timer),this._timer=null)}flush(){this.isActive()&&(this.cancel(),this._callback())}isActive(){return null!=this._timer}static debounce(e,t,i){return e instanceof Qt?e._cancelAsync():e=new Qt,e.setConfig(t,i),e}}let ei=new Set;const ti=function(e){ei.add(e)},ii=function(){const e=Boolean(ei.size);return ei.forEach(e=>{try{e.flush()}catch(e){setTimeout(()=>{throw e})}}),e};let ni="string"==typeof document.head.style.touchAction,ri="__polymerGestures",si="__polymerGesturesHandled",oi="__polymerGesturesTouchAction",ai=25,li=5,hi=2500,pi=["mousedown","mousemove","mouseup","click"],ci=[0,1,4,2],di=function(){try{return 1===new MouseEvent("test",{buttons:1}).buttons}catch(e){return!1}}();function ui(e){return pi.indexOf(e)>-1}let fi=!1;function _i(e){if(!ui(e)&&"touchend"!==e)return ni&&fi&&p?{passive:!0}:void 0}!function(){try{let e=Object.defineProperty({},"passive",{get(){fi=!0}});window.addEventListener("test",null,e),window.removeEventListener("test",null,e)}catch(e){}}();let mi=navigator.userAgent.match(/iP(?:[oa]d|hone)|Android/);const yi=[],gi={button:!0,input:!0,keygen:!0,meter:!0,output:!0,textarea:!0,progress:!0,select:!0},bi={button:!0,command:!0,fieldset:!0,input:!0,keygen:!0,optgroup:!0,option:!0,select:!0,textarea:!0};function vi(e){let t=Array.prototype.slice.call(e.labels||[]);if(!t.length){t=[];let i=e.getRootNode();if(e.id){let n=i.querySelectorAll(`label[for = ${e.id}]`);for(let e=0;e<n.length;e++)t.push(n[e])}}return t}let wi=function(e){let t=e.sourceCapabilities;var i;if((!t||t.firesTouchEvents)&&(e[si]={skip:!0},"click"===e.type)){let t=!1,n=Ei(e);for(let e=0;e<n.length;e++){if(n[e].nodeType===Node.ELEMENT_NODE)if("label"===n[e].localName)yi.push(n[e]);else if(i=n[e],gi[i.localName]){let i=vi(n[e]);for(let e=0;e<i.length;e++)t=t||yi.indexOf(i[e])>-1}if(n[e]===Pi.mouse.target)return}if(t)return;e.preventDefault(),e.stopPropagation()}};function Ci(e){let t=mi?["click"]:pi;for(let i,n=0;n<t.length;n++)i=t[n],e?(yi.length=0,document.addEventListener(i,wi,!0)):document.removeEventListener(i,wi,!0)}function xi(e){let t=e.type;if(!ui(t))return!1;if("mousemove"===t){let t=void 0===e.buttons?1:e.buttons;return e instanceof window.MouseEvent&&!di&&(t=ci[e.which]||0),Boolean(1&t)}return 0===(void 0===e.button?0:e.button)}let Pi={mouse:{target:null,mouseIgnoreJob:null},touch:{x:0,y:0,id:-1,scrollDecided:!1}};function Si(e,t,i){e.movefn=t,e.upfn=i,document.addEventListener("mousemove",t),document.addEventListener("mouseup",i)}function Oi(e){document.removeEventListener("mousemove",e.movefn),document.removeEventListener("mouseup",e.upfn),e.movefn=null,e.upfn=null}_&&document.addEventListener("touchend",function(e){if(!_)return;Pi.mouse.mouseIgnoreJob||Ci(!0),Pi.mouse.target=Ei(e)[0],Pi.mouse.mouseIgnoreJob=Qt.debounce(Pi.mouse.mouseIgnoreJob,Q.after(hi),function(){Ci(),Pi.mouse.target=null,Pi.mouse.mouseIgnoreJob=null})},!!fi&&{passive:!0});const Ei=window.ShadyDOM&&window.ShadyDOM.noPatch?window.ShadyDOM.composedPath:e=>e.composedPath&&e.composedPath()||[],Ti={},Ai=[];function Ni(e){const t=Ei(e);return t.length>0?t[0]:e.target}function ki(e){let t,i=e.type,n=e.currentTarget[ri];if(!n)return;let r=n[i];if(r){if(!e[si]&&(e[si]={},"touch"===i.slice(0,5))){let t=(e=e).changedTouches[0];if("touchstart"===i&&1===e.touches.length&&(Pi.touch.id=t.identifier),Pi.touch.id!==t.identifier)return;ni||"touchstart"!==i&&"touchmove"!==i||function(e){let t=e.changedTouches[0],i=e.type;if("touchstart"===i)Pi.touch.x=t.clientX,Pi.touch.y=t.clientY,Pi.touch.scrollDecided=!1;else if("touchmove"===i){if(Pi.touch.scrollDecided)return;Pi.touch.scrollDecided=!0;let i=function(e){let t="auto",i=Ei(e);for(let e,n=0;n<i.length;n++)if((e=i[n])[oi]){t=e[oi];break}return t}(e),n=!1,r=Math.abs(Pi.touch.x-t.clientX),s=Math.abs(Pi.touch.y-t.clientY);e.cancelable&&("none"===i?n=!0:"pan-x"===i?n=s>r:"pan-y"===i&&(n=r>s)),n?e.preventDefault():Di("track")}}(e)}if(!(t=e[si]).skip){for(let i,n=0;n<Ai.length;n++)r[(i=Ai[n]).name]&&!t[i.name]&&i.flow&&i.flow.start.indexOf(e.type)>-1&&i.reset&&i.reset();for(let n,s=0;s<Ai.length;s++)r[(n=Ai[s]).name]&&!t[n.name]&&(t[n.name]=!0,n[i](e))}}}function Ii(e,t,i){return!!Ti[t]&&(function(e,t,i){let n=Ti[t],r=n.deps,s=n.name,o=e[ri];o||(e[ri]=o={});for(let t,i,n=0;n<r.length;n++)t=r[n],mi&&ui(t)&&"click"!==t||((i=o[t])||(o[t]=i={_count:0}),0===i._count&&e.addEventListener(t,ki,_i(t)),i[s]=(i[s]||0)+1,i._count=(i._count||0)+1);e.addEventListener(t,i),n.touchAction&&Mi(e,n.touchAction)}(e,t,i),!0)}function Ri(e,t,i){return!!Ti[t]&&(function(e,t,i){let n=Ti[t],r=n.deps,s=n.name,o=e[ri];if(o)for(let t,i,n=0;n<r.length;n++)t=r[n],(i=o[t])&&i[s]&&(i[s]=(i[s]||1)-1,i._count=(i._count||1)-1,0===i._count&&e.removeEventListener(t,ki,_i(t)));e.removeEventListener(t,i)}(e,t,i),!0)}function zi(e){Ai.push(e);for(let t=0;t<e.emits.length;t++)Ti[e.emits[t]]=e}function Mi(e,t){ni&&e instanceof HTMLElement&&ee.run(()=>{e.style.touchAction=t}),e[oi]=t}function Li(e,t,i){let n=new Event(t,{bubbles:!0,cancelable:!0,composed:!0});if(n.detail=i,R(e).dispatchEvent(n),n.defaultPrevented){let e=i.preventer||i.sourceEvent;e&&e.preventDefault&&e.preventDefault()}}function Di(e){let t=function(e){for(let t,i=0;i<Ai.length;i++){t=Ai[i];for(let i,n=0;n<t.emits.length;n++)if((i=t.emits[n])===e)return t}return null}(e);t.info&&(t.info.prevent=!0)}function Fi(e,t,i,n){t&&Li(t,e,{x:i.clientX,y:i.clientY,sourceEvent:i,preventer:n,prevent:function(e){return Di(e)}})}function Bi(e,t,i){if(e.prevent)return!1;if(e.started)return!0;let n=Math.abs(e.x-t),r=Math.abs(e.y-i);return n>=li||r>=li}function Hi(e,t,i){if(!t)return;let n,r=e.moves[e.moves.length-2],s=e.moves[e.moves.length-1],o=s.x-e.x,a=s.y-e.y,l=0;r&&(n=s.x-r.x,l=s.y-r.y),Li(t,"track",{state:e.state,x:i.clientX,y:i.clientY,dx:o,dy:a,ddx:n,ddy:l,sourceEvent:i,hover:function(){return function(e,t){let i=document.elementFromPoint(e,t),n=i;for(;n&&n.shadowRoot&&!window.ShadyDOM&&n!==(n=n.shadowRoot.elementFromPoint(e,t));)n&&(i=n);return i}(i.clientX,i.clientY)}})}function ji(e,t,i){let n=Math.abs(t.clientX-e.x),r=Math.abs(t.clientY-e.y),s=Ni(i||t);!s||bi[s.localName]&&s.hasAttribute("disabled")||(isNaN(n)||isNaN(r)||n<=ai&&r<=ai||function(e){if("click"===e.type){if(0===e.detail)return!0;let t=Ni(e);if(!t.nodeType||t.nodeType!==Node.ELEMENT_NODE)return!0;let i=t.getBoundingClientRect(),n=e.pageX,r=e.pageY;return!(n>=i.left&&n<=i.right&&r>=i.top&&r<=i.bottom)}return!1}(t))&&(e.prevent||Li(s,"tap",{x:t.clientX,y:t.clientY,sourceEvent:t,preventer:i}))}zi({name:"downup",deps:["mousedown","touchstart","touchend"],flow:{start:["mousedown","touchstart"],end:["mouseup","touchend"]},emits:["down","up"],info:{movefn:null,upfn:null},reset:function(){Oi(this.info)},mousedown:function(e){if(!xi(e))return;let t=Ni(e),i=this;Si(this.info,function(e){xi(e)||(Fi("up",t,e),Oi(i.info))},function(e){xi(e)&&Fi("up",t,e),Oi(i.info)}),Fi("down",t,e)},touchstart:function(e){Fi("down",Ni(e),e.changedTouches[0],e)},touchend:function(e){Fi("up",Ni(e),e.changedTouches[0],e)}}),zi({name:"track",touchAction:"none",deps:["mousedown","touchstart","touchmove","touchend"],flow:{start:["mousedown","touchstart"],end:["mouseup","touchend"]},emits:["track"],info:{x:0,y:0,state:"start",started:!1,moves:[],addMove:function(e){this.moves.length>2&&this.moves.shift(),this.moves.push(e)},movefn:null,upfn:null,prevent:!1},reset:function(){this.info.state="start",this.info.started=!1,this.info.moves=[],this.info.x=0,this.info.y=0,this.info.prevent=!1,Oi(this.info)},mousedown:function(e){if(!xi(e))return;let t=Ni(e),i=this,n=function(e){let n=e.clientX,r=e.clientY;Bi(i.info,n,r)&&(i.info.state=i.info.started?"mouseup"===e.type?"end":"track":"start","start"===i.info.state&&Di("tap"),i.info.addMove({x:n,y:r}),xi(e)||(i.info.state="end",Oi(i.info)),t&&Hi(i.info,t,e),i.info.started=!0)};Si(this.info,n,function(e){i.info.started&&n(e),Oi(i.info)}),this.info.x=e.clientX,this.info.y=e.clientY},touchstart:function(e){let t=e.changedTouches[0];this.info.x=t.clientX,this.info.y=t.clientY},touchmove:function(e){let t=Ni(e),i=e.changedTouches[0],n=i.clientX,r=i.clientY;Bi(this.info,n,r)&&("start"===this.info.state&&Di("tap"),this.info.addMove({x:n,y:r}),Hi(this.info,t,i),this.info.state="track",this.info.started=!0)},touchend:function(e){let t=Ni(e),i=e.changedTouches[0];this.info.started&&(this.info.state="end",this.info.addMove({x:i.clientX,y:i.clientY}),Hi(this.info,t,i))}}),zi({name:"tap",deps:["mousedown","click","touchstart","touchend"],flow:{start:["mousedown","touchstart"],end:["click","touchend"]},emits:["tap"],info:{x:NaN,y:NaN,prevent:!1},reset:function(){this.info.x=NaN,this.info.y=NaN,this.info.prevent=!1},mousedown:function(e){xi(e)&&(this.info.x=e.clientX,this.info.y=e.clientY)},click:function(e){xi(e)&&ji(this.info,e)},touchstart:function(e){const t=e.changedTouches[0];this.info.x=t.clientX,this.info.y=t.clientY},touchend:function(e){ji(this.info,e.changedTouches[0],e)}});const $i=Ii,qi=y(e=>{return class extends e{_addEventListenerToNode(e,t,i){Ii(e,t,i)||super._addEventListenerToNode(e,t,i)}_removeEventListenerFromNode(e,t,i){Ri(e,t,i)||super._removeEventListenerFromNode(e,t,i)}}}),Yi=/:host\(:dir\((ltr|rtl)\)\)/g,Ui=':host([dir="$1"])',Vi=/([\s\w-#\.\[\]\*]*):dir\((ltr|rtl)\)/g,Xi=':host([dir="$2"]) $1',Ji=/:dir\((?:ltr|rtl)\)/,Wi=Boolean(window.ShadyDOM&&window.ShadyDOM.inUse),Zi=[];let Ki=null,Gi="";function Qi(){Gi=document.documentElement.getAttribute("dir")}function en(e){if(!e.__autoDirOptOut){e.setAttribute("dir",Gi)}}function tn(){Qi(),Gi=document.documentElement.getAttribute("dir");for(let e=0;e<Zi.length;e++)en(Zi[e])}const nn=y(e=>{Wi||Ki||(Qi(),(Ki=new MutationObserver(tn)).observe(document.documentElement,{attributes:!0,attributeFilter:["dir"]}));const t=se(e);class i extends t{static _processStyleText(e,i){return e=t._processStyleText.call(this,e,i),!Wi&&Ji.test(e)&&(e=this._replaceDirInCssText(e),this.__activateDir=!0),e}static _replaceDirInCssText(e){let t=e;return t=(t=t.replace(Yi,Ui)).replace(Vi,Xi)}constructor(){super(),this.__autoDirOptOut=!1}ready(){super.ready(),this.__autoDirOptOut=this.hasAttribute("dir")}connectedCallback(){t.prototype.connectedCallback&&super.connectedCallback(),this.constructor.__activateDir&&(Ki&&Ki.takeRecords().length&&tn(),Zi.push(this),en(this))}disconnectedCallback(){if(t.prototype.disconnectedCallback&&super.disconnectedCallback(),this.constructor.__activateDir){const e=Zi.indexOf(this);e>-1&&Zi.splice(e,1)}}}return i.__activateDir=!1,i});function rn(){document.body.removeAttribute("unresolved")}function sn(e,t,i){return{index:e,removed:t,addedCount:i}}"interactive"===document.readyState||"complete"===document.readyState?rn():window.addEventListener("DOMContentLoaded",rn);const on=0,an=1,ln=2,hn=3;function pn(e,t,i,n,r,s){let o,a=0,l=0,h=Math.min(i-t,s-r);if(0==t&&0==r&&(a=function(e,t,i){for(let n=0;n<i;n++)if(!dn(e[n],t[n]))return n;return i}(e,n,h)),i==e.length&&s==n.length&&(l=function(e,t,i){let n=e.length,r=t.length,s=0;for(;s<i&&dn(e[--n],t[--r]);)s++;return s}(e,n,h-a)),r+=a,s-=l,(i-=l)-(t+=a)==0&&s-r==0)return[];if(t==i){for(o=sn(t,[],0);r<s;)o.removed.push(n[r++]);return[o]}if(r==s)return[sn(t,[],i-t)];let p=function(e){let t=e.length-1,i=e[0].length-1,n=e[t][i],r=[];for(;t>0||i>0;){if(0==t){r.push(ln),i--;continue}if(0==i){r.push(hn),t--;continue}let s,o=e[t-1][i-1],a=e[t-1][i],l=e[t][i-1];(s=a<l?a<o?a:o:l<o?l:o)==o?(o==n?r.push(on):(r.push(an),n=o),t--,i--):s==a?(r.push(hn),t--,n=a):(r.push(ln),i--,n=l)}return r.reverse(),r}(function(e,t,i,n,r,s){let o=s-r+1,a=i-t+1,l=new Array(o);for(let e=0;e<o;e++)l[e]=new Array(a),l[e][0]=e;for(let e=0;e<a;e++)l[0][e]=e;for(let i=1;i<o;i++)for(let s=1;s<a;s++)if(dn(e[t+s-1],n[r+i-1]))l[i][s]=l[i-1][s-1];else{let e=l[i-1][s]+1,t=l[i][s-1]+1;l[i][s]=e<t?e:t}return l}(e,t,i,n,r,s));o=void 0;let c=[],d=t,u=r;for(let e=0;e<p.length;e++)switch(p[e]){case on:o&&(c.push(o),o=void 0),d++,u++;break;case an:o||(o=sn(d,[],0)),o.addedCount++,d++,o.removed.push(n[u]),u++;break;case ln:o||(o=sn(d,[],0)),o.addedCount++,d++;break;case hn:o||(o=sn(d,[],0)),o.removed.push(n[u]),u++}return o&&c.push(o),c}function cn(e,t){return pn(e,0,e.length,t,0,t.length)}function dn(e,t){return e===t}function un(e){return"slot"===e.localName}let fn=class{static getFlattenedNodes(e){const t=R(e);return un(e)?(e=e,t.assignedNodes({flatten:!0})):Array.from(t.childNodes).map(e=>un(e)?R(e=e).assignedNodes({flatten:!0}):[e]).reduce((e,t)=>e.concat(t),[])}constructor(e,t){this._shadyChildrenObserver=null,this._nativeChildrenObserver=null,this._connected=!1,this._target=e,this.callback=t,this._effectiveNodes=[],this._observer=null,this._scheduled=!1,this._boundSchedule=(()=>{this._schedule()}),this.connect(),this._schedule()}connect(){un(this._target)?this._listenSlots([this._target]):R(this._target).children&&(this._listenSlots(R(this._target).children),window.ShadyDOM?this._shadyChildrenObserver=ShadyDOM.observeChildren(this._target,e=>{this._processMutations(e)}):(this._nativeChildrenObserver=new MutationObserver(e=>{this._processMutations(e)}),this._nativeChildrenObserver.observe(this._target,{childList:!0}))),this._connected=!0}disconnect(){un(this._target)?this._unlistenSlots([this._target]):R(this._target).children&&(this._unlistenSlots(R(this._target).children),window.ShadyDOM&&this._shadyChildrenObserver?(ShadyDOM.unobserveChildren(this._shadyChildrenObserver),this._shadyChildrenObserver=null):this._nativeChildrenObserver&&(this._nativeChildrenObserver.disconnect(),this._nativeChildrenObserver=null)),this._connected=!1}_schedule(){this._scheduled||(this._scheduled=!0,ee.run(()=>this.flush()))}_processMutations(e){this._processSlotMutations(e),this.flush()}_processSlotMutations(e){if(e)for(let t=0;t<e.length;t++){let i=e[t];i.addedNodes&&this._listenSlots(i.addedNodes),i.removedNodes&&this._unlistenSlots(i.removedNodes)}}flush(){if(!this._connected)return!1;window.ShadyDOM&&ShadyDOM.flush(),this._nativeChildrenObserver?this._processSlotMutations(this._nativeChildrenObserver.takeRecords()):this._shadyChildrenObserver&&this._processSlotMutations(this._shadyChildrenObserver.takeRecords()),this._scheduled=!1;let e={target:this._target,addedNodes:[],removedNodes:[]},t=this.constructor.getFlattenedNodes(this._target),i=cn(t,this._effectiveNodes);for(let t,n=0;n<i.length&&(t=i[n]);n++)for(let i,n=0;n<t.removed.length&&(i=t.removed[n]);n++)e.removedNodes.push(i);for(let n,r=0;r<i.length&&(n=i[r]);r++)for(let i=n.index;i<n.index+n.addedCount;i++)e.addedNodes.push(t[i]);this._effectiveNodes=t;let n=!1;return(e.addedNodes.length||e.removedNodes.length)&&(n=!0,this.callback.call(this._target,e)),n}_listenSlots(e){for(let t=0;t<e.length;t++){let i=e[t];un(i)&&i.addEventListener("slotchange",this._boundSchedule)}}_unlistenSlots(e){for(let t=0;t<e.length;t++){let i=e[t];un(i)&&i.removeEventListener("slotchange",this._boundSchedule)}}};const _n=function(){let e,t;do{e=window.ShadyDOM&&ShadyDOM.flush(),window.ShadyCSS&&window.ShadyCSS.ScopingShim&&window.ShadyCSS.ScopingShim.flush(),t=ii()}while(e||t)},mn=Element.prototype,yn=mn.matches||mn.matchesSelector||mn.mozMatchesSelector||mn.msMatchesSelector||mn.oMatchesSelector||mn.webkitMatchesSelector,gn=function(e,t){return yn.call(e,t)};class bn{constructor(e){window.ShadyDOM&&window.ShadyDOM.inUse&&window.ShadyDOM.patch(e),this.node=e}observeNodes(e){return new fn(this.node,e)}unobserveNodes(e){e.disconnect()}notifyObserver(){}deepContains(e){if(R(this.node).contains(e))return!0;let t=e,i=e.ownerDocument;for(;t&&t!==i&&t!==this.node;)t=R(t).parentNode||R(t).host;return t===this.node}getOwnerRoot(){return R(this.node).getRootNode()}getDistributedNodes(){return"slot"===this.node.localName?R(this.node).assignedNodes({flatten:!0}):[]}getDestinationInsertionPoints(){let e=[],t=R(this.node).assignedSlot;for(;t;)e.push(t),t=R(t).assignedSlot;return e}importNode(e,t){let i=this.node instanceof Document?this.node:this.node.ownerDocument;return R(i).importNode(e,t)}getEffectiveChildNodes(){return fn.getFlattenedNodes(this.node)}queryDistributedElements(e){let t=this.getEffectiveChildNodes(),i=[];for(let n,r=0,s=t.length;r<s&&(n=t[r]);r++)n.nodeType===Node.ELEMENT_NODE&&gn(n,e)&&i.push(n);return i}get activeElement(){let e=this.node;return void 0!==e._activeElement?e._activeElement:e.activeElement}}function vn(e,t){for(let i=0;i<t.length;i++){let n=t[i];Object.defineProperty(e,n,{get:function(){return this.node[n]},configurable:!0})}}class wn{constructor(e){this.event=e}get rootTarget(){return this.path[0]}get localTarget(){return this.event.target}get path(){return this.event.composedPath()}}bn.prototype.cloneNode,bn.prototype.appendChild,bn.prototype.insertBefore,bn.prototype.removeChild,bn.prototype.replaceChild,bn.prototype.setAttribute,bn.prototype.removeAttribute,bn.prototype.querySelector,bn.prototype.querySelectorAll,bn.prototype.parentNode,bn.prototype.firstChild,bn.prototype.lastChild,bn.prototype.nextSibling,bn.prototype.previousSibling,bn.prototype.firstElementChild,bn.prototype.lastElementChild,bn.prototype.nextElementSibling,bn.prototype.previousElementSibling,bn.prototype.childNodes,bn.prototype.children,bn.prototype.classList,bn.prototype.textContent,bn.prototype.innerHTML;let Cn=bn;if(window.ShadyDOM&&window.ShadyDOM.inUse&&window.ShadyDOM.noPatch&&window.ShadyDOM.Wrapper){class e extends window.ShadyDOM.Wrapper{}Object.getOwnPropertyNames(bn.prototype).forEach(t=>{"activeElement"!=t&&(e.prototype[t]=bn.prototype[t])}),vn(e.prototype,["classList"]),Cn=e,Object.defineProperties(wn.prototype,{localTarget:{get(){const e=this.event.currentTarget,t=e&&xn(e).getOwnerRoot(),i=this.path;for(let e=0;e<i.length;e++){const n=i[e];if(xn(n).getOwnerRoot()===t)return n}},configurable:!0},path:{get(){return window.ShadyDOM.composedPath(this.event)},configurable:!0}})}else!function(e,t){for(let i=0;i<t.length;i++){let n=t[i];e[n]=function(){return this.node[n].apply(this.node,arguments)}}}(bn.prototype,["cloneNode","appendChild","insertBefore","removeChild","replaceChild","setAttribute","removeAttribute","querySelector","querySelectorAll"]),vn(bn.prototype,["parentNode","firstChild","lastChild","nextSibling","previousSibling","firstElementChild","lastElementChild","nextElementSibling","previousElementSibling","childNodes","children","classList"]),function(e,t){for(let i=0;i<t.length;i++){let n=t[i];Object.defineProperty(e,n,{get:function(){return this.node[n]},set:function(e){this.node[n]=e},configurable:!0})}}(bn.prototype,["textContent","innerHTML","className"]);const xn=function(e){if((e=e||document)instanceof Cn)return e;if(e instanceof wn)return e;let t=e.__domApi;return t||(t=e instanceof Event?new wn(e):new Cn(e),e.__domApi=t),t},Pn=window.ShadyDOM,Sn=window.ShadyCSS;function On(e,t){return R(e).getRootNode()===t}let En=window.ShadyCSS;const Tn=y(e=>{const t=nn(qi(Ve(e))),i={x:"pan-x",y:"pan-y",none:"none",all:"auto"};class n extends t{constructor(){super(),this.isAttached,this.__boundListeners,this._debouncers}static get importMeta(){return this.prototype.importMeta}created(){}connectedCallback(){super.connectedCallback(),this.isAttached=!0,this.attached()}attached(){}disconnectedCallback(){super.disconnectedCallback(),this.isAttached=!1,this.detached()}detached(){}attributeChangedCallback(e,t,i,n){t!==i&&(super.attributeChangedCallback(e,t,i,n),this.attributeChanged(e,t,i))}attributeChanged(e,t,i){}_initializeProperties(){let e=Object.getPrototypeOf(this);e.hasOwnProperty("__hasRegisterFinished")||(this._registered(),e.__hasRegisterFinished=!0),super._initializeProperties(),this.root=this,this.created(),this._applyListeners()}_registered(){}ready(){this._ensureAttributes(),super.ready()}_ensureAttributes(){}_applyListeners(){}serialize(e){return this._serializeValue(e)}deserialize(e,t){return this._deserializeValue(e,t)}reflectPropertyToAttribute(e,t,i){this._propertyToAttribute(e,t,i)}serializeValueToAttribute(e,t,i){this._valueToNodeAttribute(i||this,e,t)}extend(e,t){if(!e||!t)return e||t;let i=Object.getOwnPropertyNames(t);for(let n,r=0;r<i.length&&(n=i[r]);r++){let i=Object.getOwnPropertyDescriptor(t,n);i&&Object.defineProperty(e,n,i)}return e}mixin(e,t){for(let i in t)e[i]=t[i];return e}chainObject(e,t){return e&&t&&e!==t&&(e.__proto__=t),e}instanceTemplate(e){let t=this.constructor._contentForTemplate(e);return document.importNode(t,!0)}fire(e,t,i){i=i||{},t=null==t?{}:t;let n=new Event(e,{bubbles:void 0===i.bubbles||i.bubbles,cancelable:Boolean(i.cancelable),composed:void 0===i.composed||i.composed});n.detail=t;let r=i.node||this;return R(r).dispatchEvent(n),n}listen(e,t,i){e=e||this;let n=this.__boundListeners||(this.__boundListeners=new WeakMap),r=n.get(e);r||(r={},n.set(e,r));let s=t+i;r[s]||(r[s]=this._addMethodEventListenerToNode(e,t,i,this))}unlisten(e,t,i){e=e||this;let n=this.__boundListeners&&this.__boundListeners.get(e),r=t+i,s=n&&n[r];s&&(this._removeEventListenerFromNode(e,t,s),n[r]=null)}setScrollDirection(e,t){Mi(t||this,i[e]||"auto")}$$(e){return this.root.querySelector(e)}get domHost(){let e=R(this).getRootNode();return e instanceof DocumentFragment?e.host:e}distributeContent(){const e=xn(this);window.ShadyDOM&&e.shadowRoot&&ShadyDOM.flush()}getEffectiveChildNodes(){return xn(this).getEffectiveChildNodes()}queryDistributedElements(e){return xn(this).queryDistributedElements(e)}getEffectiveChildren(){return this.getEffectiveChildNodes().filter(function(e){return e.nodeType===Node.ELEMENT_NODE})}getEffectiveTextContent(){let e=this.getEffectiveChildNodes(),t=[];for(let i,n=0;i=e[n];n++)i.nodeType!==Node.COMMENT_NODE&&t.push(i.textContent);return t.join("")}queryEffectiveChildren(e){let t=this.queryDistributedElements(e);return t&&t[0]}queryAllEffectiveChildren(e){return this.queryDistributedElements(e)}getContentChildNodes(e){let t=this.root.querySelector(e||"slot");return t?xn(t).getDistributedNodes():[]}getContentChildren(e){return this.getContentChildNodes(e).filter(function(e){return e.nodeType===Node.ELEMENT_NODE})}isLightDescendant(e){return this!==e&&R(this).contains(e)&&R(this).getRootNode()===R(e).getRootNode()}isLocalDescendant(e){return this.root===R(e).getRootNode()}scopeSubtree(e,t=!1){return function(e,t=!1){if(!Pn||!Sn)return null;if(!Pn.handlesDynamicScoping)return null;const i=Sn.ScopingShim;if(!i)return null;const n=i.scopeForNode(e),r=R(e).getRootNode(),s=e=>{if(!On(e,r))return;const t=Array.from(Pn.nativeMethods.querySelectorAll.call(e,"*"));t.push(e);for(let e=0;e<t.length;e++){const s=t[e];if(!On(s,r))continue;const o=i.currentScopeForNode(s);o!==n&&(""!==o&&i.unscopeNode(s,o),i.scopeNode(s,n))}};if(s(e),t){const t=new MutationObserver(e=>{for(let t=0;t<e.length;t++){const i=e[t];for(let e=0;e<i.addedNodes.length;e++){const t=i.addedNodes[e];t.nodeType===Node.ELEMENT_NODE&&s(t)}}});return t.observe(e,{childList:!0,subtree:!0}),t}return null}(e,t)}getComputedStyleValue(e){return En.getComputedStyleValue(this,e)}debounce(e,t,i){return this._debouncers=this._debouncers||{},this._debouncers[e]=Qt.debounce(this._debouncers[e],i>0?Q.after(i):ee,t.bind(this))}isDebouncerActive(e){this._debouncers=this._debouncers||{};let t=this._debouncers[e];return!(!t||!t.isActive())}flushDebouncer(e){this._debouncers=this._debouncers||{};let t=this._debouncers[e];t&&t.flush()}cancelDebouncer(e){this._debouncers=this._debouncers||{};let t=this._debouncers[e];t&&t.cancel()}async(e,t){return t>0?Q.run(e.bind(this),t):~ee.run(e.bind(this))}cancelAsync(e){e<0?ee.cancel(~e):Q.cancel(e)}create(e,t){let i=document.createElement(e);if(t)if(i.setProperties)i.setProperties(t);else for(let e in t)i[e]=t[e];return i}elementMatches(e,t){return gn(t||this,e)}toggleAttribute(e,t){let i=this;return 3===arguments.length&&(i=arguments[2]),1==arguments.length&&(t=!i.hasAttribute(e)),t?(R(i).setAttribute(e,""),!0):(R(i).removeAttribute(e),!1)}toggleClass(e,t,i){i=i||this,1==arguments.length&&(t=!i.classList.contains(e)),t?i.classList.add(e):i.classList.remove(e)}transform(e,t){(t=t||this).style.webkitTransform=e,t.style.transform=e}translate3d(e,t,i,n){n=n||this,this.transform("translate3d("+e+","+t+","+i+")",n)}arrayDelete(e,t){let i;if(Array.isArray(e)){if((i=e.indexOf(t))>=0)return e.splice(i,1)}else{if((i=j(this,e).indexOf(t))>=0)return this.splice(e,i,1)}return null}_logger(e,t){switch(Array.isArray(t)&&1===t.length&&Array.isArray(t[0])&&(t=t[0]),e){case"log":case"warn":case"error":console[e](...t)}}_log(...e){this._logger("log",e)}_warn(...e){this._logger("warn",e)}_error(...e){this._logger("error",e)}_logf(e,...t){return["[%s::%s]",this.is,e,...t]}}return n.prototype.is="",n}),An={attached:!0,detached:!0,ready:!0,created:!0,beforeRegister:!0,registered:!0,attributeChanged:!0,listeners:!0,hostAttributes:!0},Nn={attached:!0,detached:!0,ready:!0,created:!0,beforeRegister:!0,registered:!0,attributeChanged:!0,behaviors:!0,_noAccessors:!0},kn=Object.assign({listeners:!0,hostAttributes:!0,properties:!0,observers:!0},Nn);function In(e,t,i,n){!function(e,t,i){const n=e._noAccessors,r=Object.getOwnPropertyNames(e);for(let s=0;s<r.length;s++){let o=r[s];if(!(o in i))if(n)t[o]=e[o];else{let i=Object.getOwnPropertyDescriptor(e,o);i&&(i.configurable=!0,Object.defineProperty(t,o,i))}}}(t,e,n);for(let e in An)t[e]&&(i[e]=i[e]||[],i[e].push(t[e]))}function Rn(e,t){for(const i in t){const n=e[i],r=t[i];e[i]=!("value"in r)&&n&&"value"in n?Object.assign({value:n.value},r):r}}function zn(e,t,i){let n;const r={};class s extends t{static _finalizeClass(){if(this.hasOwnProperty(JSCompiler_renameProperty("generatedFrom",this))){if(n)for(let e,t=0;t<n.length;t++)(e=n[t]).properties&&this.createProperties(e.properties),e.observers&&this.createObservers(e.observers,e.properties);e.properties&&this.createProperties(e.properties),e.observers&&this.createObservers(e.observers,e.properties),this._prepareTemplate()}else t._finalizeClass.call(this)}static get properties(){const t={};if(n)for(let e=0;e<n.length;e++)Rn(t,n[e].properties);return Rn(t,e.properties),t}static get observers(){let t=[];if(n)for(let e,i=0;i<n.length;i++)(e=n[i]).observers&&(t=t.concat(e.observers));return e.observers&&(t=t.concat(e.observers)),t}created(){super.created();const e=r.created;if(e)for(let t=0;t<e.length;t++)e[t].call(this)}_registered(){const e=s.prototype;if(!e.hasOwnProperty("__hasRegisterFinished")){e.__hasRegisterFinished=!0,super._registered(),u&&o(e);const t=Object.getPrototypeOf(this);let i=r.beforeRegister;if(i)for(let e=0;e<i.length;e++)i[e].call(t);if(i=r.registered)for(let e=0;e<i.length;e++)i[e].call(t)}}_applyListeners(){super._applyListeners();const e=r.listeners;if(e)for(let t=0;t<e.length;t++){const i=e[t];if(i)for(let e in i)this._addMethodEventListenerToNode(this,e,i[e])}}_ensureAttributes(){const e=r.hostAttributes;if(e)for(let t=e.length-1;t>=0;t--){const i=e[t];for(let e in i)this._ensureAttribute(e,i[e])}super._ensureAttributes()}ready(){super.ready();let e=r.ready;if(e)for(let t=0;t<e.length;t++)e[t].call(this)}attached(){super.attached();let e=r.attached;if(e)for(let t=0;t<e.length;t++)e[t].call(this)}detached(){super.detached();let e=r.detached;if(e)for(let t=0;t<e.length;t++)e[t].call(this)}attributeChanged(e,t,i){super.attributeChanged();let n=r.attributeChanged;if(n)for(let r=0;r<n.length;r++)n[r].call(this,e,t,i)}}if(i){Array.isArray(i)||(i=[i]);let e=t.prototype.behaviors;n=function e(t,i,n){i=i||[];for(let r=t.length-1;r>=0;r--){let s=t[r];s?Array.isArray(s)?e(s,i):i.indexOf(s)<0&&(!n||n.indexOf(s)<0)&&i.unshift(s):console.warn("behavior is null, check for missing or 404 import")}return i}(i,null,e),s.prototype.behaviors=e?e.concat(i):n}const o=t=>{n&&function(e,t,i){for(let n=0;n<t.length;n++)In(e,t[n],i,kn)}(t,n,r),In(t,e,r,Nn)};return u||o(s.prototype),s.generatedFrom=e,s}const Mn=function(e){let t;return t="function"==typeof e?e:Mn.Class(e),customElements.define(t.is,t),t};function Ln(e,t,i,n,r){let s;r&&(s="object"==typeof i&&null!==i)&&(n=e.__dataTemp[t]);let o=n!==i&&(n==n||i==i);return s&&o&&(e.__dataTemp[t]=i),o}Mn.Class=function(e,t){e||console.warn("Polymer.Class requires `info` argument");let i=t?t(Tn(HTMLElement)):Tn(HTMLElement);return(i=zn(e,i,e.behaviors)).is=i.prototype.is=e.is,i};const Dn=y(e=>{return class extends e{_shouldPropertyChange(e,t,i){return Ln(this,e,t,i,!0)}}}),Fn=y(e=>{return class extends e{static get properties(){return{mutableData:Boolean}}_shouldPropertyChange(e,t,i){return Ln(this,e,t,i,this.mutableData)}}});Dn._mutablePropertyChange=Ln;let Bn=null;function Hn(){return Bn}Hn.prototype=Object.create(HTMLTemplateElement.prototype,{constructor:{value:Hn,writable:!0}});const jn=je(Hn),$n=Dn(jn);const qn=je(class{});class Yn extends qn{constructor(e){super(),this._configureProperties(e),this.root=this._stampTemplate(this.__dataHost);let t=[];this.children=t;for(let e=this.root.firstChild;e;e=e.nextSibling)t.push(e),e.__templatizeInstance=this;this.__templatizeOwner&&this.__templatizeOwner.__hideTemplateChildren__&&this._showHideChildren(!0);let i=this.__templatizeOptions;(e&&i.instanceProps||!i.instanceProps)&&this._enableProperties()}_configureProperties(e){if(this.__templatizeOptions.forwardHostProp)for(let e in this.__hostProps)this._setPendingProperty(e,this.__dataHost["_host_"+e]);for(let t in e)this._setPendingProperty(t,e[t])}forwardHostProp(e,t){this._setPendingPropertyOrPath(e,t,!1,!0)&&this.__dataHost._enqueueClient(this)}_addEventListenerToNode(e,t,i){if(this._methodHost&&this.__templatizeOptions.parentModel)this._methodHost._addEventListenerToNode(e,t,e=>{e.model=this,i(e)});else{let n=this.__dataHost.__dataHost;n&&n._addEventListenerToNode(e,t,i)}}_showHideChildren(e){let t=this.children;for(let i=0;i<t.length;i++){let n=t[i];if(Boolean(e)!=Boolean(n.__hideTemplateChildren__))if(n.nodeType===Node.TEXT_NODE)e?(n.__polymerTextContent__=n.textContent,n.textContent=""):n.textContent=n.__polymerTextContent__;else if("slot"===n.localName)if(e)n.__polymerReplaced__=document.createComment("hidden-slot"),R(R(n).parentNode).replaceChild(n.__polymerReplaced__,n);else{const e=n.__polymerReplaced__;e&&R(R(e).parentNode).replaceChild(n,e)}else n.style&&(e?(n.__polymerDisplay__=n.style.display,n.style.display="none"):n.style.display=n.__polymerDisplay__);n.__hideTemplateChildren__=e,n._showHideChildren&&n._showHideChildren(e)}}_setUnmanagedPropertyToNode(e,t,i){e.__hideTemplateChildren__&&e.nodeType==Node.TEXT_NODE&&"textContent"==t?e.__polymerTextContent__=i:super._setUnmanagedPropertyToNode(e,t,i)}get parentModel(){let e=this.__parentModel;if(!e){let t;e=this;do{e=e.__dataHost.__dataHost}while((t=e.__templatizeOptions)&&!t.parentModel);this.__parentModel=e}return e}dispatchEvent(e){return!0}}Yn.prototype.__dataHost,Yn.prototype.__templatizeOptions,Yn.prototype._methodHost,Yn.prototype.__templatizeOwner,Yn.prototype.__hostProps;const Un=Dn(Yn);function Vn(e){let t=e.__dataHost;return t&&t._methodHost||t}function Xn(e,t,i){let n=i.mutableData?Un:Yn;Kn.mixin&&(n=Kn.mixin(n));let r=class extends n{};return r.prototype.__templatizeOptions=i,r.prototype._bindTemplate(e),function(e,t,i,n){let r=i.hostProps||{};for(let t in n.instanceProps){delete r[t];let i=n.notifyInstanceProp;i&&e.prototype._addPropertyEffect(t,e.prototype.PROPERTY_EFFECT_TYPES.NOTIFY,{fn:Zn(t,i)})}if(n.forwardHostProp&&t.__dataHost)for(let t in r)i.hasHostProps||(i.hasHostProps=!0),e.prototype._addPropertyEffect(t,e.prototype.PROPERTY_EFFECT_TYPES.NOTIFY,{fn:function(e,t,i){e.__dataHost._setPendingPropertyOrPath("_host_"+t,i[t],!0,!0)}})}(r,e,t,i),r}function Jn(e,t,i){let n=i.forwardHostProp;if(n&&t.hasHostProps){let r=t.templatizeTemplateClass;if(!r){let e=i.mutableData?$n:jn;r=t.templatizeTemplateClass=class extends e{};let s=t.hostProps;for(let e in s)r.prototype._addPropertyEffect("_host_"+e,r.prototype.PROPERTY_EFFECT_TYPES.PROPAGATE,{fn:Wn(e,n)}),r.prototype._createNotifyingProperty("_host_"+e)}!function(e,t){Bn=e,Object.setPrototypeOf(e,t.prototype),new t,Bn=null}(e,r),e.__dataProto&&Object.assign(e.__data,e.__dataProto),e.__dataTemp={},e.__dataPending=null,e.__dataOld=null,e._enableProperties()}}function Wn(e,t){return function(e,i,n){t.call(e.__templatizeOwner,i.substring("_host_".length),n[i])}}function Zn(e,t){return function(e,i,n){t.call(e.__templatizeOwner,e,i,n[i])}}function Kn(e,t,i){if(c&&!Vn(e))throw new Error("strictTemplatePolicy: template owner not trusted");if(i=i||{},e.__templatizeOwner)throw new Error("A <template> can only be templatized once");e.__templatizeOwner=t;let n=(t?t.constructor:Yn)._parseTemplate(e),r=n.templatizeInstanceClass;r||(r=Xn(e,n,i),n.templatizeInstanceClass=r),Jn(e,n,i);let s=class extends r{};return s.prototype._methodHost=Vn(e),s.prototype.__dataHost=e,s.prototype.__templatizeOwner=t,s.prototype.__hostProps=n.hostProps,s=s}let Gn=!1;function Qn(){if(u&&!a){if(!Gn){Gn=!0;const e=document.createElement("style");e.textContent="dom-bind,dom-if,dom-repeat{display:none;}",document.head.appendChild(e)}return!0}return!1}const er=qi(Fn(je(HTMLElement)));customElements.define("dom-bind",class extends er{static get observedAttributes(){return["mutable-data"]}constructor(){if(super(),c)throw new Error("strictTemplatePolicy: dom-bind not allowed");this.root=null,this.$=null,this.__children=null}attributeChangedCallback(e,t,i,n){this.mutableData=!0}connectedCallback(){Qn()||(this.style.display="none"),this.render()}disconnectedCallback(){this.__removeChildren()}__insertChildren(){R(R(this).parentNode).insertBefore(this.root,this)}__removeChildren(){if(this.__children)for(let e=0;e<this.__children.length;e++)this.root.appendChild(this.__children[e])}render(){let e;if(!this.__children){if(!(e=e||this.querySelector("template"))){let t=new MutationObserver(()=>{if(!(e=this.querySelector("template")))throw new Error("dom-bind requires a <template> child");t.disconnect(),this.render()});return void t.observe(this,{childList:!0})}this.root=this._stampTemplate(e),this.$=this.root.$,this.__children=[];for(let e=this.root.firstChild;e;e=e.nextSibling)this.__children[this.__children.length]=e;this._enableProperties()}this.__insertChildren(),this.dispatchEvent(new CustomEvent("dom-change",{bubbles:!0,composed:!0}))}});const tr=Fn(Ze);class ir extends tr{static get is(){return"dom-repeat"}static get template(){return null}static get properties(){return{items:{type:Array},as:{type:String,value:"item"},indexAs:{type:String,value:"index"},itemsIndexAs:{type:String,value:"itemsIndex"},sort:{type:Function,observer:"__sortChanged"},filter:{type:Function,observer:"__filterChanged"},observe:{type:String,observer:"__observeChanged"},delay:Number,renderedItemCount:{type:Number,notify:!0,readOnly:!0},initialCount:{type:Number,observer:"__initializeChunking"},targetFramerate:{type:Number,value:20},_targetFrameTime:{type:Number,computed:"__computeFrameTime(targetFramerate)"}}}static get observers(){return["__itemsChanged(items.*)"]}constructor(){super(),this.__instances=[],this.__limit=1/0,this.__pool=[],this.__renderDebouncer=null,this.__itemsIdxToInstIdx={},this.__chunkCount=null,this.__lastChunkTime=null,this.__sortFn=null,this.__filterFn=null,this.__observePaths=null,this.__ctor=null,this.__isDetached=!0,this.template=null}disconnectedCallback(){super.disconnectedCallback(),this.__isDetached=!0;for(let e=0;e<this.__instances.length;e++)this.__detachInstance(e)}connectedCallback(){if(super.connectedCallback(),Qn()||(this.style.display="none"),this.__isDetached){this.__isDetached=!1;let e=R(R(this).parentNode);for(let t=0;t<this.__instances.length;t++)this.__attachInstance(t,e)}}__ensureTemplatized(){if(!this.__ctor){let e=this.template=this.querySelector("template");if(!e){let e=new MutationObserver(()=>{if(!this.querySelector("template"))throw new Error("dom-repeat requires a <template> child");e.disconnect(),this.__render()});return e.observe(this,{childList:!0}),!1}let t={};t[this.as]=!0,t[this.indexAs]=!0,t[this.itemsIndexAs]=!0,this.__ctor=Kn(e,this,{mutableData:this.mutableData,parentModel:!0,instanceProps:t,forwardHostProp:function(e,t){let i=this.__instances;for(let n,r=0;r<i.length&&(n=i[r]);r++)n.forwardHostProp(e,t)},notifyInstanceProp:function(e,t,i){if((n=this.as)===(r=t)||L(n,r)||D(n,r)){let n=e[this.itemsIndexAs];t==this.as&&(this.items[n]=i);let r=F(this.as,`${JSCompiler_renameProperty("items",this)}.${n}`,t);this.notifyPath(r,i)}var n,r}})}return!0}__getMethodHost(){return this.__dataHost._methodHost||this.__dataHost}__functionFromPropertyValue(e){if("string"==typeof e){let t=e,i=this.__getMethodHost();return function(){return i[t].apply(i,arguments)}}return e}__sortChanged(e){this.__sortFn=this.__functionFromPropertyValue(e),this.items&&this.__debounceRender(this.__render)}__filterChanged(e){this.__filterFn=this.__functionFromPropertyValue(e),this.items&&this.__debounceRender(this.__render)}__computeFrameTime(e){return Math.ceil(1e3/e)}__initializeChunking(){this.initialCount&&(this.__limit=this.initialCount,this.__chunkCount=this.initialCount,this.__lastChunkTime=performance.now())}__tryRenderChunk(){this.items&&this.__limit<this.items.length&&this.__debounceRender(this.__requestRenderChunk)}__requestRenderChunk(){requestAnimationFrame(()=>this.__renderChunk())}__renderChunk(){let e=performance.now(),t=this._targetFrameTime/(e-this.__lastChunkTime);this.__chunkCount=Math.round(this.__chunkCount*t)||1,this.__limit+=this.__chunkCount,this.__lastChunkTime=e,this.__debounceRender(this.__render)}__observeChanged(){this.__observePaths=this.observe&&this.observe.replace(".*",".").split(" ")}__itemsChanged(e){this.items&&!Array.isArray(this.items)&&console.warn("dom-repeat expected array for `items`, found",this.items),this.__handleItemPath(e.path,e.value)||(this.__initializeChunking(),this.__debounceRender(this.__render))}__handleObservedPaths(e){if(this.__sortFn||this.__filterFn)if(e){if(this.__observePaths){let t=this.__observePaths;for(let i=0;i<t.length;i++)0===e.indexOf(t[i])&&this.__debounceRender(this.__render,this.delay)}}else this.__debounceRender(this.__render,this.delay)}__debounceRender(e,t=0){this.__renderDebouncer=Qt.debounce(this.__renderDebouncer,t>0?Q.after(t):ee,e.bind(this)),ti(this.__renderDebouncer)}render(){this.__debounceRender(this.__render),_n()}__render(){this.__ensureTemplatized()&&(this.__applyFullRefresh(),this.__pool.length=0,this._setRenderedItemCount(this.__instances.length),this.dispatchEvent(new CustomEvent("dom-change",{bubbles:!0,composed:!0})),this.__tryRenderChunk())}__applyFullRefresh(){let e=this.items||[],t=new Array(e.length);for(let i=0;i<e.length;i++)t[i]=i;this.__filterFn&&(t=t.filter((t,i,n)=>this.__filterFn(e[t],i,n))),this.__sortFn&&t.sort((t,i)=>this.__sortFn(e[t],e[i]));const i=this.__itemsIdxToInstIdx={};let n=0;const r=Math.min(t.length,this.__limit);for(;n<r;n++){let r=this.__instances[n],s=t[n],o=e[s];i[s]=n,r?(r._setPendingProperty(this.as,o),r._setPendingProperty(this.indexAs,n),r._setPendingProperty(this.itemsIndexAs,s),r._flushProperties()):this.__insertInstance(o,n,s)}for(let e=this.__instances.length-1;e>=n;e--)this.__detachAndRemoveInstance(e)}__detachInstance(e){let t=this.__instances[e];const i=R(t.root);for(let e=0;e<t.children.length;e++){let n=t.children[e];i.appendChild(n)}return t}__attachInstance(e,t){let i=this.__instances[e];t.insertBefore(i.root,this)}__detachAndRemoveInstance(e){let t=this.__detachInstance(e);t&&this.__pool.push(t),this.__instances.splice(e,1)}__stampInstance(e,t,i){let n={};return n[this.as]=e,n[this.indexAs]=t,n[this.itemsIndexAs]=i,new this.__ctor(n)}__insertInstance(e,t,i){let n=this.__pool.pop();n?(n._setPendingProperty(this.as,e),n._setPendingProperty(this.indexAs,t),n._setPendingProperty(this.itemsIndexAs,i),n._flushProperties()):n=this.__stampInstance(e,t,i);let r=this.__instances[t+1],s=r?r.children[0]:this;return R(R(this).parentNode).insertBefore(n.root,s),this.__instances[t]=n,n}_showHideChildren(e){for(let t=0;t<this.__instances.length;t++)this.__instances[t]._showHideChildren(e)}__handleItemPath(e,t){let i=e.slice(6),n=i.indexOf("."),r=n<0?i:i.substring(0,n);if(r==parseInt(r,10)){let e=n<0?"":i.substring(n+1);this.__handleObservedPaths(e);let s=this.__itemsIdxToInstIdx[r],o=this.__instances[s];if(o){let i=this.as+(e?"."+e:"");o._setPendingPropertyOrPath(i,t,!1,!0),o._flushProperties()}return!0}}itemForElement(e){let t=this.modelForElement(e);return t&&t[this.as]}indexForElement(e){let t=this.modelForElement(e);return t&&t[this.indexAs]}modelForElement(e){return function(e,t){let i;for(;t;)if(i=t.__templatizeInstance){if(i.__dataHost==e)return i;t=i.__dataHost}else t=R(t).parentNode;return null}(this.template,e)}}customElements.define(ir.is,ir);class nr extends Ze{static get is(){return"dom-if"}static get template(){return null}static get properties(){return{if:{type:Boolean,observer:"__debounceRender"},restamp:{type:Boolean,observer:"__debounceRender"}}}constructor(){super(),this.__renderDebouncer=null,this.__invalidProps=null,this.__instance=null,this._lastIf=!1,this.__ctor=null,this.__hideTemplateChildren__=!1}__debounceRender(){this.__renderDebouncer=Qt.debounce(this.__renderDebouncer,ee,()=>this.__render()),ti(this.__renderDebouncer)}disconnectedCallback(){super.disconnectedCallback();const e=R(this).parentNode;e&&(e.nodeType!=Node.DOCUMENT_FRAGMENT_NODE||R(e).host)||this.__teardownInstance()}connectedCallback(){super.connectedCallback(),Qn()||(this.style.display="none"),this.if&&this.__debounceRender()}render(){_n()}__render(){if(this.if){if(!this.__ensureInstance())return;this._showHideChildren()}else this.restamp&&this.__teardownInstance();!this.restamp&&this.__instance&&this._showHideChildren(),this.if!=this._lastIf&&(this.dispatchEvent(new CustomEvent("dom-change",{bubbles:!0,composed:!0})),this._lastIf=this.if)}__ensureInstance(){let e=R(this).parentNode;if(e){if(!this.__ctor){let e=R(this).querySelector("template");if(!e){let e=new MutationObserver(()=>{if(!R(this).querySelector("template"))throw new Error("dom-if requires a <template> child");e.disconnect(),this.__render()});return e.observe(this,{childList:!0}),!1}this.__ctor=Kn(e,this,{mutableData:!0,forwardHostProp:function(e,t){this.__instance&&(this.if?this.__instance.forwardHostProp(e,t):(this.__invalidProps=this.__invalidProps||Object.create(null),this.__invalidProps[M(e)]=!0))}})}if(this.__instance){this.__syncHostProperties();let t=this.__instance.children;if(t&&t.length){if(R(this).previousSibling!==t[t.length-1])for(let i,n=0;n<t.length&&(i=t[n]);n++)R(e).insertBefore(i,this)}}else this.__instance=new this.__ctor,R(e).insertBefore(this.__instance.root,this)}return!0}__syncHostProperties(){let e=this.__invalidProps;if(e){for(let t in e)this.__instance._setPendingProperty(t,this.__dataHost[t]);this.__invalidProps=null,this.__instance._flushProperties()}}__teardownInstance(){if(this.__instance){let e=this.__instance.children;if(e&&e.length){let t=R(e[0]).parentNode;if(t){t=R(t);for(let i,n=0;n<e.length&&(i=e[n]);n++)t.removeChild(i)}}this.__instance=null,this.__invalidProps=null}}_showHideChildren(){let e=this.__hideTemplateChildren__||!this.if;this.__instance&&this.__instance._showHideChildren(e)}}customElements.define(nr.is,nr);let rr=y(e=>{let t=Ve(e);return class extends t{static get properties(){return{items:{type:Array},multi:{type:Boolean,value:!1},selected:{type:Object,notify:!0},selectedItem:{type:Object,notify:!0},toggle:{type:Boolean,value:!1}}}static get observers(){return["__updateSelection(multi, items.*)"]}constructor(){super(),this.__lastItems=null,this.__lastMulti=null,this.__selectedMap=null}__updateSelection(e,t){let i=t.path;if(i==JSCompiler_renameProperty("items",this)){let i=t.base||[],n=this.__lastItems;if(e!==this.__lastMulti&&this.clearSelection(),n){let e=cn(i,n);this.__applySplices(e)}this.__lastItems=i,this.__lastMulti=e}else if(t.path==`${JSCompiler_renameProperty("items",this)}.splices`)this.__applySplices(t.value.indexSplices);else{let e=i.slice(`${JSCompiler_renameProperty("items",this)}.`.length),t=parseInt(e,10);e.indexOf(".")<0&&e==t&&this.__deselectChangedIdx(t)}}__applySplices(e){let t=this.__selectedMap;for(let i=0;i<e.length;i++){let n=e[i];t.forEach((e,i)=>{e<n.index||(e>=n.index+n.removed.length?t.set(i,e+n.addedCount-n.removed.length):t.set(i,-1))});for(let e=0;e<n.addedCount;e++){let i=n.index+e;t.has(this.items[i])&&t.set(this.items[i],i)}}this.__updateLinks();let i=0;t.forEach((e,n)=>{e<0?(this.multi?this.splice(JSCompiler_renameProperty("selected",this),i,1):this.selected=this.selectedItem=null,t.delete(n)):i++})}__updateLinks(){if(this.__dataLinkedPaths={},this.multi){let e=0;this.__selectedMap.forEach(t=>{t>=0&&this.linkPaths(`${JSCompiler_renameProperty("items",this)}.${t}`,`${JSCompiler_renameProperty("selected",this)}.${e++}`)})}else this.__selectedMap.forEach(e=>{this.linkPaths(JSCompiler_renameProperty("selected",this),`${JSCompiler_renameProperty("items",this)}.${e}`),this.linkPaths(JSCompiler_renameProperty("selectedItem",this),`${JSCompiler_renameProperty("items",this)}.${e}`)})}clearSelection(){this.__dataLinkedPaths={},this.__selectedMap=new Map,this.selected=this.multi?[]:null,this.selectedItem=null}isSelected(e){return this.__selectedMap.has(e)}isIndexSelected(e){return this.isSelected(this.items[e])}__deselectChangedIdx(e){let t=this.__selectedIndexForItemIndex(e);if(t>=0){let e=0;this.__selectedMap.forEach((i,n)=>{t==e++&&this.deselect(n)})}}__selectedIndexForItemIndex(e){let t=this.__dataLinkedPaths[`${JSCompiler_renameProperty("items",this)}.${e}`];if(t)return parseInt(t.slice(`${JSCompiler_renameProperty("selected",this)}.`.length),10)}deselect(e){let t=this.__selectedMap.get(e);if(t>=0){let i;this.__selectedMap.delete(e),this.multi&&(i=this.__selectedIndexForItemIndex(t)),this.__updateLinks(),this.multi?this.splice(JSCompiler_renameProperty("selected",this),i,1):this.selected=this.selectedItem=null}}deselectIndex(e){this.deselect(this.items[e])}select(e){this.selectIndex(this.items.indexOf(e))}selectIndex(e){let t=this.items[e];this.isSelected(t)?this.toggle&&this.deselectIndex(e):(this.multi||this.__selectedMap.clear(),this.__selectedMap.set(t,e),this.__updateLinks(),this.multi?this.push(JSCompiler_renameProperty("selected",this),t):this.selected=this.selectedItem=t)}}})(Ze);class sr extends rr{static get is(){return"array-selector"}static get template(){return null}}customElements.define(sr.is,sr);const or=new Zt;window.ShadyCSS||(window.ShadyCSS={prepareTemplate(e,t,i){},prepareTemplateDom(e,t){},prepareTemplateStyles(e,t,i){},styleSubtree(e,t){or.processStyles(),Ot(e,t)},styleElement(e){or.processStyles()},styleDocument(e){or.processStyles(),Ot(document.body,e)},getComputedStyleValue:(e,t)=>Et(e,t),flushCustomStyles(){},nativeCss:it,nativeShadow:Ke,cssBuild:Qe,disableRuntime:tt}),window.ShadyCSS.CustomStyleInterface=or;const ar="include",lr=window.ShadyCSS.CustomStyleInterface;window.customElements.define("custom-style",class extends HTMLElement{constructor(){super(),this._style=null,lr.addCustomStyle(this)}getStyle(){if(this._style)return this._style;const e=this.querySelector("style");if(!e)return null;this._style=e;const t=e.getAttribute(ar);return t&&(e.removeAttribute(ar),e.textContent=function(e){let t=e.trim().split(/\s+/),i="";for(let e=0;e<t.length;e++)i+=I(t[e]);return i}(t)+e.textContent),this.ownerDocument!==window.document&&window.document.head.appendChild(this),this._style}});Tn(HTMLElement).prototype;const hr=We`
<custom-style>
  <style is="custom-style">
    [hidden] {
      display: none !important;
    }
  </style>
</custom-style>
<custom-style>
  <style is="custom-style">
    html {

      --layout: {
        display: -ms-flexbox;
        display: -webkit-flex;
        display: flex;
      };

      --layout-inline: {
        display: -ms-inline-flexbox;
        display: -webkit-inline-flex;
        display: inline-flex;
      };

      --layout-horizontal: {
        @apply --layout;

        -ms-flex-direction: row;
        -webkit-flex-direction: row;
        flex-direction: row;
      };

      --layout-horizontal-reverse: {
        @apply --layout;

        -ms-flex-direction: row-reverse;
        -webkit-flex-direction: row-reverse;
        flex-direction: row-reverse;
      };

      --layout-vertical: {
        @apply --layout;

        -ms-flex-direction: column;
        -webkit-flex-direction: column;
        flex-direction: column;
      };

      --layout-vertical-reverse: {
        @apply --layout;

        -ms-flex-direction: column-reverse;
        -webkit-flex-direction: column-reverse;
        flex-direction: column-reverse;
      };

      --layout-wrap: {
        -ms-flex-wrap: wrap;
        -webkit-flex-wrap: wrap;
        flex-wrap: wrap;
      };

      --layout-wrap-reverse: {
        -ms-flex-wrap: wrap-reverse;
        -webkit-flex-wrap: wrap-reverse;
        flex-wrap: wrap-reverse;
      };

      --layout-flex-auto: {
        -ms-flex: 1 1 auto;
        -webkit-flex: 1 1 auto;
        flex: 1 1 auto;
      };

      --layout-flex-none: {
        -ms-flex: none;
        -webkit-flex: none;
        flex: none;
      };

      --layout-flex: {
        -ms-flex: 1 1 0.000000001px;
        -webkit-flex: 1;
        flex: 1;
        -webkit-flex-basis: 0.000000001px;
        flex-basis: 0.000000001px;
      };

      --layout-flex-2: {
        -ms-flex: 2;
        -webkit-flex: 2;
        flex: 2;
      };

      --layout-flex-3: {
        -ms-flex: 3;
        -webkit-flex: 3;
        flex: 3;
      };

      --layout-flex-4: {
        -ms-flex: 4;
        -webkit-flex: 4;
        flex: 4;
      };

      --layout-flex-5: {
        -ms-flex: 5;
        -webkit-flex: 5;
        flex: 5;
      };

      --layout-flex-6: {
        -ms-flex: 6;
        -webkit-flex: 6;
        flex: 6;
      };

      --layout-flex-7: {
        -ms-flex: 7;
        -webkit-flex: 7;
        flex: 7;
      };

      --layout-flex-8: {
        -ms-flex: 8;
        -webkit-flex: 8;
        flex: 8;
      };

      --layout-flex-9: {
        -ms-flex: 9;
        -webkit-flex: 9;
        flex: 9;
      };

      --layout-flex-10: {
        -ms-flex: 10;
        -webkit-flex: 10;
        flex: 10;
      };

      --layout-flex-11: {
        -ms-flex: 11;
        -webkit-flex: 11;
        flex: 11;
      };

      --layout-flex-12: {
        -ms-flex: 12;
        -webkit-flex: 12;
        flex: 12;
      };

      /* alignment in cross axis */

      --layout-start: {
        -ms-flex-align: start;
        -webkit-align-items: flex-start;
        align-items: flex-start;
      };

      --layout-center: {
        -ms-flex-align: center;
        -webkit-align-items: center;
        align-items: center;
      };

      --layout-end: {
        -ms-flex-align: end;
        -webkit-align-items: flex-end;
        align-items: flex-end;
      };

      --layout-baseline: {
        -ms-flex-align: baseline;
        -webkit-align-items: baseline;
        align-items: baseline;
      };

      /* alignment in main axis */

      --layout-start-justified: {
        -ms-flex-pack: start;
        -webkit-justify-content: flex-start;
        justify-content: flex-start;
      };

      --layout-center-justified: {
        -ms-flex-pack: center;
        -webkit-justify-content: center;
        justify-content: center;
      };

      --layout-end-justified: {
        -ms-flex-pack: end;
        -webkit-justify-content: flex-end;
        justify-content: flex-end;
      };

      --layout-around-justified: {
        -ms-flex-pack: distribute;
        -webkit-justify-content: space-around;
        justify-content: space-around;
      };

      --layout-justified: {
        -ms-flex-pack: justify;
        -webkit-justify-content: space-between;
        justify-content: space-between;
      };

      --layout-center-center: {
        @apply --layout-center;
        @apply --layout-center-justified;
      };

      /* self alignment */

      --layout-self-start: {
        -ms-align-self: flex-start;
        -webkit-align-self: flex-start;
        align-self: flex-start;
      };

      --layout-self-center: {
        -ms-align-self: center;
        -webkit-align-self: center;
        align-self: center;
      };

      --layout-self-end: {
        -ms-align-self: flex-end;
        -webkit-align-self: flex-end;
        align-self: flex-end;
      };

      --layout-self-stretch: {
        -ms-align-self: stretch;
        -webkit-align-self: stretch;
        align-self: stretch;
      };

      --layout-self-baseline: {
        -ms-align-self: baseline;
        -webkit-align-self: baseline;
        align-self: baseline;
      };

      /* multi-line alignment in main axis */

      --layout-start-aligned: {
        -ms-flex-line-pack: start;  /* IE10 */
        -ms-align-content: flex-start;
        -webkit-align-content: flex-start;
        align-content: flex-start;
      };

      --layout-end-aligned: {
        -ms-flex-line-pack: end;  /* IE10 */
        -ms-align-content: flex-end;
        -webkit-align-content: flex-end;
        align-content: flex-end;
      };

      --layout-center-aligned: {
        -ms-flex-line-pack: center;  /* IE10 */
        -ms-align-content: center;
        -webkit-align-content: center;
        align-content: center;
      };

      --layout-between-aligned: {
        -ms-flex-line-pack: justify;  /* IE10 */
        -ms-align-content: space-between;
        -webkit-align-content: space-between;
        align-content: space-between;
      };

      --layout-around-aligned: {
        -ms-flex-line-pack: distribute;  /* IE10 */
        -ms-align-content: space-around;
        -webkit-align-content: space-around;
        align-content: space-around;
      };

      /*******************************
                Other Layout
      *******************************/

      --layout-block: {
        display: block;
      };

      --layout-invisible: {
        visibility: hidden !important;
      };

      --layout-relative: {
        position: relative;
      };

      --layout-fit: {
        position: absolute;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
      };

      --layout-scroll: {
        -webkit-overflow-scrolling: touch;
        overflow: auto;
      };

      --layout-fullbleed: {
        margin: 0;
        height: 100vh;
      };

      /* fixed position */

      --layout-fixed-top: {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
      };

      --layout-fixed-right: {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
      };

      --layout-fixed-bottom: {
        position: fixed;
        right: 0;
        bottom: 0;
        left: 0;
      };

      --layout-fixed-left: {
        position: fixed;
        top: 0;
        bottom: 0;
        left: 0;
      };

    }
  </style>
</custom-style>`;hr.setAttribute("style","display: none;"),document.head.appendChild(hr.content);var pr=document.createElement("style");pr.textContent="[hidden] { display: none !important; }",document.head.appendChild(pr);const cr=We`
<custom-style>
  <style is="custom-style">
    html {

      /* Material Design color palette for Google products */

      --google-red-100: #f4c7c3;
      --google-red-300: #e67c73;
      --google-red-500: #db4437;
      --google-red-700: #c53929;

      --google-blue-100: #c6dafc;
      --google-blue-300: #7baaf7;
      --google-blue-500: #4285f4;
      --google-blue-700: #3367d6;

      --google-green-100: #b7e1cd;
      --google-green-300: #57bb8a;
      --google-green-500: #0f9d58;
      --google-green-700: #0b8043;

      --google-yellow-100: #fce8b2;
      --google-yellow-300: #f7cb4d;
      --google-yellow-500: #f4b400;
      --google-yellow-700: #f09300;

      --google-grey-100: #f5f5f5;
      --google-grey-300: #e0e0e0;
      --google-grey-500: #9e9e9e;
      --google-grey-700: #616161;

      /* Material Design color palette from online spec document */

      --paper-red-50: #ffebee;
      --paper-red-100: #ffcdd2;
      --paper-red-200: #ef9a9a;
      --paper-red-300: #e57373;
      --paper-red-400: #ef5350;
      --paper-red-500: #f44336;
      --paper-red-600: #e53935;
      --paper-red-700: #d32f2f;
      --paper-red-800: #c62828;
      --paper-red-900: #b71c1c;
      --paper-red-a100: #ff8a80;
      --paper-red-a200: #ff5252;
      --paper-red-a400: #ff1744;
      --paper-red-a700: #d50000;

      --paper-pink-50: #fce4ec;
      --paper-pink-100: #f8bbd0;
      --paper-pink-200: #f48fb1;
      --paper-pink-300: #f06292;
      --paper-pink-400: #ec407a;
      --paper-pink-500: #e91e63;
      --paper-pink-600: #d81b60;
      --paper-pink-700: #c2185b;
      --paper-pink-800: #ad1457;
      --paper-pink-900: #880e4f;
      --paper-pink-a100: #ff80ab;
      --paper-pink-a200: #ff4081;
      --paper-pink-a400: #f50057;
      --paper-pink-a700: #c51162;

      --paper-purple-50: #f3e5f5;
      --paper-purple-100: #e1bee7;
      --paper-purple-200: #ce93d8;
      --paper-purple-300: #ba68c8;
      --paper-purple-400: #ab47bc;
      --paper-purple-500: #9c27b0;
      --paper-purple-600: #8e24aa;
      --paper-purple-700: #7b1fa2;
      --paper-purple-800: #6a1b9a;
      --paper-purple-900: #4a148c;
      --paper-purple-a100: #ea80fc;
      --paper-purple-a200: #e040fb;
      --paper-purple-a400: #d500f9;
      --paper-purple-a700: #aa00ff;

      --paper-deep-purple-50: #ede7f6;
      --paper-deep-purple-100: #d1c4e9;
      --paper-deep-purple-200: #b39ddb;
      --paper-deep-purple-300: #9575cd;
      --paper-deep-purple-400: #7e57c2;
      --paper-deep-purple-500: #673ab7;
      --paper-deep-purple-600: #5e35b1;
      --paper-deep-purple-700: #512da8;
      --paper-deep-purple-800: #4527a0;
      --paper-deep-purple-900: #311b92;
      --paper-deep-purple-a100: #b388ff;
      --paper-deep-purple-a200: #7c4dff;
      --paper-deep-purple-a400: #651fff;
      --paper-deep-purple-a700: #6200ea;

      --paper-indigo-50: #e8eaf6;
      --paper-indigo-100: #c5cae9;
      --paper-indigo-200: #9fa8da;
      --paper-indigo-300: #7986cb;
      --paper-indigo-400: #5c6bc0;
      --paper-indigo-500: #3f51b5;
      --paper-indigo-600: #3949ab;
      --paper-indigo-700: #303f9f;
      --paper-indigo-800: #283593;
      --paper-indigo-900: #1a237e;
      --paper-indigo-a100: #8c9eff;
      --paper-indigo-a200: #536dfe;
      --paper-indigo-a400: #3d5afe;
      --paper-indigo-a700: #304ffe;

      --paper-blue-50: #e3f2fd;
      --paper-blue-100: #bbdefb;
      --paper-blue-200: #90caf9;
      --paper-blue-300: #64b5f6;
      --paper-blue-400: #42a5f5;
      --paper-blue-500: #2196f3;
      --paper-blue-600: #1e88e5;
      --paper-blue-700: #1976d2;
      --paper-blue-800: #1565c0;
      --paper-blue-900: #0d47a1;
      --paper-blue-a100: #82b1ff;
      --paper-blue-a200: #448aff;
      --paper-blue-a400: #2979ff;
      --paper-blue-a700: #2962ff;

      --paper-light-blue-50: #e1f5fe;
      --paper-light-blue-100: #b3e5fc;
      --paper-light-blue-200: #81d4fa;
      --paper-light-blue-300: #4fc3f7;
      --paper-light-blue-400: #29b6f6;
      --paper-light-blue-500: #03a9f4;
      --paper-light-blue-600: #039be5;
      --paper-light-blue-700: #0288d1;
      --paper-light-blue-800: #0277bd;
      --paper-light-blue-900: #01579b;
      --paper-light-blue-a100: #80d8ff;
      --paper-light-blue-a200: #40c4ff;
      --paper-light-blue-a400: #00b0ff;
      --paper-light-blue-a700: #0091ea;

      --paper-cyan-50: #e0f7fa;
      --paper-cyan-100: #b2ebf2;
      --paper-cyan-200: #80deea;
      --paper-cyan-300: #4dd0e1;
      --paper-cyan-400: #26c6da;
      --paper-cyan-500: #00bcd4;
      --paper-cyan-600: #00acc1;
      --paper-cyan-700: #0097a7;
      --paper-cyan-800: #00838f;
      --paper-cyan-900: #006064;
      --paper-cyan-a100: #84ffff;
      --paper-cyan-a200: #18ffff;
      --paper-cyan-a400: #00e5ff;
      --paper-cyan-a700: #00b8d4;

      --paper-teal-50: #e0f2f1;
      --paper-teal-100: #b2dfdb;
      --paper-teal-200: #80cbc4;
      --paper-teal-300: #4db6ac;
      --paper-teal-400: #26a69a;
      --paper-teal-500: #009688;
      --paper-teal-600: #00897b;
      --paper-teal-700: #00796b;
      --paper-teal-800: #00695c;
      --paper-teal-900: #004d40;
      --paper-teal-a100: #a7ffeb;
      --paper-teal-a200: #64ffda;
      --paper-teal-a400: #1de9b6;
      --paper-teal-a700: #00bfa5;

      --paper-green-50: #e8f5e9;
      --paper-green-100: #c8e6c9;
      --paper-green-200: #a5d6a7;
      --paper-green-300: #81c784;
      --paper-green-400: #66bb6a;
      --paper-green-500: #4caf50;
      --paper-green-600: #43a047;
      --paper-green-700: #388e3c;
      --paper-green-800: #2e7d32;
      --paper-green-900: #1b5e20;
      --paper-green-a100: #b9f6ca;
      --paper-green-a200: #69f0ae;
      --paper-green-a400: #00e676;
      --paper-green-a700: #00c853;

      --paper-light-green-50: #f1f8e9;
      --paper-light-green-100: #dcedc8;
      --paper-light-green-200: #c5e1a5;
      --paper-light-green-300: #aed581;
      --paper-light-green-400: #9ccc65;
      --paper-light-green-500: #8bc34a;
      --paper-light-green-600: #7cb342;
      --paper-light-green-700: #689f38;
      --paper-light-green-800: #558b2f;
      --paper-light-green-900: #33691e;
      --paper-light-green-a100: #ccff90;
      --paper-light-green-a200: #b2ff59;
      --paper-light-green-a400: #76ff03;
      --paper-light-green-a700: #64dd17;

      --paper-lime-50: #f9fbe7;
      --paper-lime-100: #f0f4c3;
      --paper-lime-200: #e6ee9c;
      --paper-lime-300: #dce775;
      --paper-lime-400: #d4e157;
      --paper-lime-500: #cddc39;
      --paper-lime-600: #c0ca33;
      --paper-lime-700: #afb42b;
      --paper-lime-800: #9e9d24;
      --paper-lime-900: #827717;
      --paper-lime-a100: #f4ff81;
      --paper-lime-a200: #eeff41;
      --paper-lime-a400: #c6ff00;
      --paper-lime-a700: #aeea00;

      --paper-yellow-50: #fffde7;
      --paper-yellow-100: #fff9c4;
      --paper-yellow-200: #fff59d;
      --paper-yellow-300: #fff176;
      --paper-yellow-400: #ffee58;
      --paper-yellow-500: #ffeb3b;
      --paper-yellow-600: #fdd835;
      --paper-yellow-700: #fbc02d;
      --paper-yellow-800: #f9a825;
      --paper-yellow-900: #f57f17;
      --paper-yellow-a100: #ffff8d;
      --paper-yellow-a200: #ffff00;
      --paper-yellow-a400: #ffea00;
      --paper-yellow-a700: #ffd600;

      --paper-amber-50: #fff8e1;
      --paper-amber-100: #ffecb3;
      --paper-amber-200: #ffe082;
      --paper-amber-300: #ffd54f;
      --paper-amber-400: #ffca28;
      --paper-amber-500: #ffc107;
      --paper-amber-600: #ffb300;
      --paper-amber-700: #ffa000;
      --paper-amber-800: #ff8f00;
      --paper-amber-900: #ff6f00;
      --paper-amber-a100: #ffe57f;
      --paper-amber-a200: #ffd740;
      --paper-amber-a400: #ffc400;
      --paper-amber-a700: #ffab00;

      --paper-orange-50: #fff3e0;
      --paper-orange-100: #ffe0b2;
      --paper-orange-200: #ffcc80;
      --paper-orange-300: #ffb74d;
      --paper-orange-400: #ffa726;
      --paper-orange-500: #ff9800;
      --paper-orange-600: #fb8c00;
      --paper-orange-700: #f57c00;
      --paper-orange-800: #ef6c00;
      --paper-orange-900: #e65100;
      --paper-orange-a100: #ffd180;
      --paper-orange-a200: #ffab40;
      --paper-orange-a400: #ff9100;
      --paper-orange-a700: #ff6500;

      --paper-deep-orange-50: #fbe9e7;
      --paper-deep-orange-100: #ffccbc;
      --paper-deep-orange-200: #ffab91;
      --paper-deep-orange-300: #ff8a65;
      --paper-deep-orange-400: #ff7043;
      --paper-deep-orange-500: #ff5722;
      --paper-deep-orange-600: #f4511e;
      --paper-deep-orange-700: #e64a19;
      --paper-deep-orange-800: #d84315;
      --paper-deep-orange-900: #bf360c;
      --paper-deep-orange-a100: #ff9e80;
      --paper-deep-orange-a200: #ff6e40;
      --paper-deep-orange-a400: #ff3d00;
      --paper-deep-orange-a700: #dd2c00;

      --paper-brown-50: #efebe9;
      --paper-brown-100: #d7ccc8;
      --paper-brown-200: #bcaaa4;
      --paper-brown-300: #a1887f;
      --paper-brown-400: #8d6e63;
      --paper-brown-500: #795548;
      --paper-brown-600: #6d4c41;
      --paper-brown-700: #5d4037;
      --paper-brown-800: #4e342e;
      --paper-brown-900: #3e2723;

      --paper-grey-50: #fafafa;
      --paper-grey-100: #f5f5f5;
      --paper-grey-200: #eeeeee;
      --paper-grey-300: #e0e0e0;
      --paper-grey-400: #bdbdbd;
      --paper-grey-500: #9e9e9e;
      --paper-grey-600: #757575;
      --paper-grey-700: #616161;
      --paper-grey-800: #424242;
      --paper-grey-900: #212121;

      --paper-blue-grey-50: #eceff1;
      --paper-blue-grey-100: #cfd8dc;
      --paper-blue-grey-200: #b0bec5;
      --paper-blue-grey-300: #90a4ae;
      --paper-blue-grey-400: #78909c;
      --paper-blue-grey-500: #607d8b;
      --paper-blue-grey-600: #546e7a;
      --paper-blue-grey-700: #455a64;
      --paper-blue-grey-800: #37474f;
      --paper-blue-grey-900: #263238;

      /* opacity for dark text on a light background */
      --dark-divider-opacity: 0.12;
      --dark-disabled-opacity: 0.38; /* or hint text or icon */
      --dark-secondary-opacity: 0.54;
      --dark-primary-opacity: 0.87;

      /* opacity for light text on a dark background */
      --light-divider-opacity: 0.12;
      --light-disabled-opacity: 0.3; /* or hint text or icon */
      --light-secondary-opacity: 0.7;
      --light-primary-opacity: 1.0;

    }

  </style>
</custom-style>
`;cr.setAttribute("style","display: none;"),document.head.appendChild(cr.content);const dr=We`
<custom-style>
  <style is="custom-style">
    html {
      /*
       * You can use these generic variables in your elements for easy theming.
       * For example, if all your elements use \`--primary-text-color\` as its main
       * color, then switching from a light to a dark theme is just a matter of
       * changing the value of \`--primary-text-color\` in your application.
       */
      --primary-text-color: var(--light-theme-text-color);
      --primary-background-color: var(--light-theme-background-color);
      --secondary-text-color: var(--light-theme-secondary-color);
      --disabled-text-color: var(--light-theme-disabled-color);
      --divider-color: var(--light-theme-divider-color);
      --error-color: var(--paper-deep-orange-a700);

      /*
       * Primary and accent colors. Also see color.js for more colors.
       */
      --primary-color: var(--paper-indigo-500);
      --light-primary-color: var(--paper-indigo-100);
      --dark-primary-color: var(--paper-indigo-700);

      --accent-color: var(--paper-pink-a200);
      --light-accent-color: var(--paper-pink-a100);
      --dark-accent-color: var(--paper-pink-a400);


      /*
       * Material Design Light background theme
       */
      --light-theme-background-color: #ffffff;
      --light-theme-base-color: #000000;
      --light-theme-text-color: var(--paper-grey-900);
      --light-theme-secondary-color: #737373;  /* for secondary text and icons */
      --light-theme-disabled-color: #9b9b9b;  /* disabled/hint text */
      --light-theme-divider-color: #dbdbdb;

      /*
       * Material Design Dark background theme
       */
      --dark-theme-background-color: var(--paper-grey-900);
      --dark-theme-base-color: #ffffff;
      --dark-theme-text-color: #ffffff;
      --dark-theme-secondary-color: #bcbcbc;  /* for secondary text and icons */
      --dark-theme-disabled-color: #646464;  /* disabled/hint text */
      --dark-theme-divider-color: #3c3c3c;

      /*
       * Deprecated values because of their confusing names.
       */
      --text-primary-color: var(--dark-theme-text-color);
      --default-primary-color: var(--primary-color);
    }
  </style>
</custom-style>`;if(dr.setAttribute("style","display: none;"),document.head.appendChild(dr.content),!window.polymerSkipLoadingFontRoboto){const e=document.createElement("link");e.rel="stylesheet",e.type="text/css",e.crossOrigin="anonymous",e.href="https://fonts.googleapis.com/css?family=Roboto+Mono:400,700|Roboto:400,300,300italic,400italic,500,500italic,700,700italic",document.head.appendChild(e)}const ur=We`<custom-style>
  <style is="custom-style">
    html {

      /* Shared Styles */
      --paper-font-common-base: {
        font-family: 'Roboto', 'Noto', sans-serif;
        -webkit-font-smoothing: antialiased;
      };

      --paper-font-common-code: {
        font-family: 'Roboto Mono', 'Consolas', 'Menlo', monospace;
        -webkit-font-smoothing: antialiased;
      };

      --paper-font-common-expensive-kerning: {
        text-rendering: optimizeLegibility;
      };

      --paper-font-common-nowrap: {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      };

      /* Material Font Styles */

      --paper-font-display4: {
        @apply --paper-font-common-base;
        @apply --paper-font-common-nowrap;

        font-size: 112px;
        font-weight: 300;
        letter-spacing: -.044em;
        line-height: 120px;
      };

      --paper-font-display3: {
        @apply --paper-font-common-base;
        @apply --paper-font-common-nowrap;

        font-size: 56px;
        font-weight: 400;
        letter-spacing: -.026em;
        line-height: 60px;
      };

      --paper-font-display2: {
        @apply --paper-font-common-base;

        font-size: 45px;
        font-weight: 400;
        letter-spacing: -.018em;
        line-height: 48px;
      };

      --paper-font-display1: {
        @apply --paper-font-common-base;

        font-size: 34px;
        font-weight: 400;
        letter-spacing: -.01em;
        line-height: 40px;
      };

      --paper-font-headline: {
        @apply --paper-font-common-base;

        font-size: 24px;
        font-weight: 400;
        letter-spacing: -.012em;
        line-height: 32px;
      };

      --paper-font-title: {
        @apply --paper-font-common-base;
        @apply --paper-font-common-nowrap;

        font-size: 20px;
        font-weight: 500;
        line-height: 28px;
      };

      --paper-font-subhead: {
        @apply --paper-font-common-base;

        font-size: 16px;
        font-weight: 400;
        line-height: 24px;
      };

      --paper-font-body2: {
        @apply --paper-font-common-base;

        font-size: 14px;
        font-weight: 500;
        line-height: 24px;
      };

      --paper-font-body1: {
        @apply --paper-font-common-base;

        font-size: 14px;
        font-weight: 400;
        line-height: 20px;
      };

      --paper-font-caption: {
        @apply --paper-font-common-base;
        @apply --paper-font-common-nowrap;

        font-size: 12px;
        font-weight: 400;
        letter-spacing: 0.011em;
        line-height: 20px;
      };

      --paper-font-menu: {
        @apply --paper-font-common-base;
        @apply --paper-font-common-nowrap;

        font-size: 13px;
        font-weight: 500;
        line-height: 24px;
      };

      --paper-font-button: {
        @apply --paper-font-common-base;
        @apply --paper-font-common-nowrap;

        font-size: 14px;
        font-weight: 500;
        letter-spacing: 0.018em;
        line-height: 24px;
        text-transform: uppercase;
      };

      --paper-font-code2: {
        @apply --paper-font-common-code;

        font-size: 14px;
        font-weight: 700;
        line-height: 20px;
      };

      --paper-font-code1: {
        @apply --paper-font-common-code;

        font-size: 14px;
        font-weight: 500;
        line-height: 20px;
      };

    }

  </style>
</custom-style>`;ur.setAttribute("style","display: none;"),document.head.appendChild(ur.content);const fr=We`
<custom-style>
  <style is="custom-style">
    html {

      --shadow-transition: {
        transition: box-shadow 0.28s cubic-bezier(0.4, 0, 0.2, 1);
      };

      --shadow-none: {
        box-shadow: none;
      };

      /* from http://codepen.io/shyndman/pen/c5394ddf2e8b2a5c9185904b57421cdb */

      --shadow-elevation-2dp: {
        box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.14),
                    0 1px 5px 0 rgba(0, 0, 0, 0.12),
                    0 3px 1px -2px rgba(0, 0, 0, 0.2);
      };

      --shadow-elevation-3dp: {
        box-shadow: 0 3px 4px 0 rgba(0, 0, 0, 0.14),
                    0 1px 8px 0 rgba(0, 0, 0, 0.12),
                    0 3px 3px -2px rgba(0, 0, 0, 0.4);
      };

      --shadow-elevation-4dp: {
        box-shadow: 0 4px 5px 0 rgba(0, 0, 0, 0.14),
                    0 1px 10px 0 rgba(0, 0, 0, 0.12),
                    0 2px 4px -1px rgba(0, 0, 0, 0.4);
      };

      --shadow-elevation-6dp: {
        box-shadow: 0 6px 10px 0 rgba(0, 0, 0, 0.14),
                    0 1px 18px 0 rgba(0, 0, 0, 0.12),
                    0 3px 5px -1px rgba(0, 0, 0, 0.4);
      };

      --shadow-elevation-8dp: {
        box-shadow: 0 8px 10px 1px rgba(0, 0, 0, 0.14),
                    0 3px 14px 2px rgba(0, 0, 0, 0.12),
                    0 5px 5px -3px rgba(0, 0, 0, 0.4);
      };

      --shadow-elevation-12dp: {
        box-shadow: 0 12px 16px 1px rgba(0, 0, 0, 0.14),
                    0 4px 22px 3px rgba(0, 0, 0, 0.12),
                    0 6px 7px -4px rgba(0, 0, 0, 0.4);
      };

      --shadow-elevation-16dp: {
        box-shadow: 0 16px 24px 2px rgba(0, 0, 0, 0.14),
                    0  6px 30px 5px rgba(0, 0, 0, 0.12),
                    0  8px 10px -5px rgba(0, 0, 0, 0.4);
      };

      --shadow-elevation-24dp: {
        box-shadow: 0 24px 38px 3px rgba(0, 0, 0, 0.14),
                    0 9px 46px 8px rgba(0, 0, 0, 0.12),
                    0 11px 15px -7px rgba(0, 0, 0, 0.4);
      };
    }
  </style>
</custom-style>`;fr.setAttribute("style","display: none;"),document.head.appendChild(fr.content);const _r=document.createElement("template");_r.setAttribute("style","display: none;"),_r.innerHTML='<dom-module id="paper-dialog-shared-styles">\n  <template>\n    <style>\n      :host {\n        display: block;\n        margin: 24px 40px;\n\n        background: var(--paper-dialog-background-color, var(--primary-background-color));\n        color: var(--paper-dialog-color, var(--primary-text-color));\n\n        @apply --paper-font-body1;\n        @apply --shadow-elevation-16dp;\n        @apply --paper-dialog;\n      }\n\n      :host > ::slotted(*) {\n        margin-top: 20px;\n        padding: 0 24px;\n      }\n\n      :host > ::slotted(.no-padding) {\n        padding: 0;\n      }\n\n      \n      :host > ::slotted(*:first-child) {\n        margin-top: 24px;\n      }\n\n      :host > ::slotted(*:last-child) {\n        margin-bottom: 24px;\n      }\n\n      /* In 1.x, this selector was `:host > ::content h2`. In 2.x <slot> allows\n      to select direct children only, which increases the weight of this\n      selector, so we have to re-define first-child/last-child margins below. */\n      :host > ::slotted(h2) {\n        position: relative;\n        margin: 0;\n\n        @apply --paper-font-title;\n        @apply --paper-dialog-title;\n      }\n\n      /* Apply mixin again, in case it sets margin-top. */\n      :host > ::slotted(h2:first-child) {\n        margin-top: 24px;\n        @apply --paper-dialog-title;\n      }\n\n      /* Apply mixin again, in case it sets margin-bottom. */\n      :host > ::slotted(h2:last-child) {\n        margin-bottom: 24px;\n        @apply --paper-dialog-title;\n      }\n\n      :host > ::slotted(.paper-dialog-buttons),\n      :host > ::slotted(.buttons) {\n        position: relative;\n        padding: 8px 8px 8px 24px;\n        margin: 0;\n\n        color: var(--paper-dialog-button-color, var(--primary-color));\n\n        @apply --layout-horizontal;\n        @apply --layout-end-justified;\n      }\n    </style>\n  </template>\n</dom-module>',document.head.appendChild(_r.content);const mr=[{properties:{animationConfig:{type:Object},entryAnimation:{observer:"_entryAnimationChanged",type:String},exitAnimation:{observer:"_exitAnimationChanged",type:String}},_entryAnimationChanged:function(){this.animationConfig=this.animationConfig||{},this.animationConfig.entry=[{name:this.entryAnimation,node:this}]},_exitAnimationChanged:function(){this.animationConfig=this.animationConfig||{},this.animationConfig.exit=[{name:this.exitAnimation,node:this}]},_copyProperties:function(e,t){for(var i in t)e[i]=t[i]},_cloneConfig:function(e){var t={isClone:!0};return this._copyProperties(t,e),t},_getAnimationConfigRecursive:function(e,t,i){var n;if(this.animationConfig)if(this.animationConfig.value&&"function"==typeof this.animationConfig.value)this._warn(this._logf("playAnimation","Please put 'animationConfig' inside of your components 'properties' object instead of outside of it."));else if(n=e?this.animationConfig[e]:this.animationConfig,Array.isArray(n)||(n=[n]),n)for(var r,s=0;r=n[s];s++)if(r.animatable)r.animatable._getAnimationConfigRecursive(r.type||e,t,i);else if(r.id){var o=t[r.id];o?(o.isClone||(t[r.id]=this._cloneConfig(o),o=t[r.id]),this._copyProperties(o,r)):t[r.id]=r}else i.push(r)},getAnimationConfig:function(e){var t={},i=[];for(var n in this._getAnimationConfigRecursive(e,t,i),t)i.push(t[n]);return i}},{_configureAnimations:function(e){var t=[],i=[];if(e.length>0)for(let t,n=0;t=e[n];n++){let e=document.createElement(t.name);if(e.isNeonAnimation){let n=null;e.configure||(e.configure=function(e){return null}),n=e.configure(t),i.push({result:n,config:t,neonAnimation:e})}else console.warn(this.is+":",t.name,"not found!")}for(var n=0;n<i.length;n++){let e=i[n].result,r=i[n].config,s=i[n].neonAnimation;try{"function"!=typeof e.cancel&&(e=document.timeline.play(e))}catch(t){e=null,console.warn("Couldnt play","(",r.name,").",t)}e&&t.push({neonAnimation:s,config:r,animation:e})}return t},_shouldComplete:function(e){for(var t=!0,i=0;i<e.length;i++)if("finished"!=e[i].animation.playState){t=!1;break}return t},_complete:function(e){for(var t=0;t<e.length;t++)e[t].neonAnimation.complete(e[t].config);for(t=0;t<e.length;t++)e[t].animation.cancel()},playAnimation:function(e,t){var i=this.getAnimationConfig(e);if(i){this._active=this._active||{},this._active[e]&&(this._complete(this._active[e]),delete this._active[e]);var n=this._configureAnimations(i);if(0!=n.length){this._active[e]=n;for(var r=0;r<n.length;r++)n[r].animation.onfinish=function(){this._shouldComplete(n)&&(this._complete(n),delete this._active[e],this.fire("neon-animation-finish",t,{bubbles:!1}))}.bind(this)}else this.fire("neon-animation-finish",t,{bubbles:!1})}},cancelAnimation:function(){for(var e in this._active){var t=this._active[e];for(var i in t)t[i].animation.cancel()}this._active={}}}],yr={properties:{sizingTarget:{type:Object,value:function(){return this}},fitInto:{type:Object,value:window},noOverlap:{type:Boolean},positionTarget:{type:Element},horizontalAlign:{type:String},verticalAlign:{type:String},dynamicAlign:{type:Boolean},horizontalOffset:{type:Number,value:0,notify:!0},verticalOffset:{type:Number,value:0,notify:!0},autoFitOnAttach:{type:Boolean,value:!1},_fitInfo:{type:Object}},get _fitWidth(){return this.fitInto===window?this.fitInto.innerWidth:this.fitInto.getBoundingClientRect().width},get _fitHeight(){return this.fitInto===window?this.fitInto.innerHeight:this.fitInto.getBoundingClientRect().height},get _fitLeft(){return this.fitInto===window?0:this.fitInto.getBoundingClientRect().left},get _fitTop(){return this.fitInto===window?0:this.fitInto.getBoundingClientRect().top},get _defaultPositionTarget(){var e=xn(this).parentNode;return e&&e.nodeType===Node.DOCUMENT_FRAGMENT_NODE&&(e=e.host),e},get _localeHorizontalAlign(){if(this._isRTL){if("right"===this.horizontalAlign)return"left";if("left"===this.horizontalAlign)return"right"}return this.horizontalAlign},get __shouldPosition(){return(this.horizontalAlign||this.verticalAlign)&&this.positionTarget},attached:function(){void 0===this._isRTL&&(this._isRTL="rtl"==window.getComputedStyle(this).direction),this.positionTarget=this.positionTarget||this._defaultPositionTarget,this.autoFitOnAttach&&("none"===window.getComputedStyle(this).display?setTimeout(function(){this.fit()}.bind(this)):(window.ShadyDOM&&ShadyDOM.flush(),this.fit()))},detached:function(){this.__deferredFit&&(clearTimeout(this.__deferredFit),this.__deferredFit=null)},fit:function(){this.position(),this.constrain(),this.center()},_discoverInfo:function(){if(!this._fitInfo){var e=window.getComputedStyle(this),t=window.getComputedStyle(this.sizingTarget);this._fitInfo={inlineStyle:{top:this.style.top||"",left:this.style.left||"",position:this.style.position||""},sizerInlineStyle:{maxWidth:this.sizingTarget.style.maxWidth||"",maxHeight:this.sizingTarget.style.maxHeight||"",boxSizing:this.sizingTarget.style.boxSizing||""},positionedBy:{vertically:"auto"!==e.top?"top":"auto"!==e.bottom?"bottom":null,horizontally:"auto"!==e.left?"left":"auto"!==e.right?"right":null},sizedBy:{height:"none"!==t.maxHeight,width:"none"!==t.maxWidth,minWidth:parseInt(t.minWidth,10)||0,minHeight:parseInt(t.minHeight,10)||0},margin:{top:parseInt(e.marginTop,10)||0,right:parseInt(e.marginRight,10)||0,bottom:parseInt(e.marginBottom,10)||0,left:parseInt(e.marginLeft,10)||0}}}},resetFit:function(){var e=this._fitInfo||{};for(var t in e.sizerInlineStyle)this.sizingTarget.style[t]=e.sizerInlineStyle[t];for(var t in e.inlineStyle)this.style[t]=e.inlineStyle[t];this._fitInfo=null},refit:function(){var e=this.sizingTarget.scrollLeft,t=this.sizingTarget.scrollTop;this.resetFit(),this.fit(),this.sizingTarget.scrollLeft=e,this.sizingTarget.scrollTop=t},position:function(){if(this.__shouldPosition){this._discoverInfo(),this.style.position="fixed",this.sizingTarget.style.boxSizing="border-box",this.style.left="0px",this.style.top="0px";var e=this.getBoundingClientRect(),t=this.__getNormalizedRect(this.positionTarget),i=this.__getNormalizedRect(this.fitInto),n=this._fitInfo.margin,r={width:e.width+n.left+n.right,height:e.height+n.top+n.bottom},s=this.__getPosition(this._localeHorizontalAlign,this.verticalAlign,r,e,t,i),o=s.left+n.left,a=s.top+n.top,l=Math.min(i.right-n.right,o+e.width),h=Math.min(i.bottom-n.bottom,a+e.height);o=Math.max(i.left+n.left,Math.min(o,l-this._fitInfo.sizedBy.minWidth)),a=Math.max(i.top+n.top,Math.min(a,h-this._fitInfo.sizedBy.minHeight)),this.sizingTarget.style.maxWidth=Math.max(l-o,this._fitInfo.sizedBy.minWidth)+"px",this.sizingTarget.style.maxHeight=Math.max(h-a,this._fitInfo.sizedBy.minHeight)+"px",this.style.left=o-e.left+"px",this.style.top=a-e.top+"px"}},constrain:function(){if(!this.__shouldPosition){this._discoverInfo();var e=this._fitInfo;e.positionedBy.vertically||(this.style.position="fixed",this.style.top="0px"),e.positionedBy.horizontally||(this.style.position="fixed",this.style.left="0px"),this.sizingTarget.style.boxSizing="border-box";var t=this.getBoundingClientRect();e.sizedBy.height||this.__sizeDimension(t,e.positionedBy.vertically,"top","bottom","Height"),e.sizedBy.width||this.__sizeDimension(t,e.positionedBy.horizontally,"left","right","Width")}},_sizeDimension:function(e,t,i,n,r){this.__sizeDimension(e,t,i,n,r)},__sizeDimension:function(e,t,i,n,r){var s=this._fitInfo,o=this.__getNormalizedRect(this.fitInto),a="Width"===r?o.width:o.height,l=t===n,h=l?a-e[n]:e[i],p=s.margin[l?i:n],c="offset"+r,d=this[c]-this.sizingTarget[c];this.sizingTarget.style["max"+r]=a-p-h-d+"px"},center:function(){if(!this.__shouldPosition){this._discoverInfo();var e=this._fitInfo.positionedBy;if(!e.vertically||!e.horizontally){this.style.position="fixed",e.vertically||(this.style.top="0px"),e.horizontally||(this.style.left="0px");var t=this.getBoundingClientRect(),i=this.__getNormalizedRect(this.fitInto);if(!e.vertically){var n=i.top-t.top+(i.height-t.height)/2;this.style.top=n+"px"}if(!e.horizontally){var r=i.left-t.left+(i.width-t.width)/2;this.style.left=r+"px"}}}},__getNormalizedRect:function(e){return e===document.documentElement||e===window?{top:0,left:0,width:window.innerWidth,height:window.innerHeight,right:window.innerWidth,bottom:window.innerHeight}:e.getBoundingClientRect()},__getOffscreenArea:function(e,t,i){var n=Math.min(0,e.top)+Math.min(0,i.bottom-(e.top+t.height)),r=Math.min(0,e.left)+Math.min(0,i.right-(e.left+t.width));return Math.abs(n)*t.width+Math.abs(r)*t.height},__getPosition:function(e,t,i,n,r,s){var o,a=[{verticalAlign:"top",horizontalAlign:"left",top:r.top+this.verticalOffset,left:r.left+this.horizontalOffset},{verticalAlign:"top",horizontalAlign:"right",top:r.top+this.verticalOffset,left:r.right-i.width-this.horizontalOffset},{verticalAlign:"bottom",horizontalAlign:"left",top:r.bottom-i.height-this.verticalOffset,left:r.left+this.horizontalOffset},{verticalAlign:"bottom",horizontalAlign:"right",top:r.bottom-i.height-this.verticalOffset,left:r.right-i.width-this.horizontalOffset}];if(this.noOverlap){for(var l=0,h=a.length;l<h;l++){var p={};for(var c in a[l])p[c]=a[l][c];a.push(p)}a[0].top=a[1].top+=r.height,a[2].top=a[3].top-=r.height,a[4].left=a[6].left+=r.width,a[5].left=a[7].left-=r.width}t="auto"===t?null:t,(e="auto"===e?null:e)&&"center"!==e||(a.push({verticalAlign:"top",horizontalAlign:"center",top:r.top+this.verticalOffset+(this.noOverlap?r.height:0),left:r.left-n.width/2+r.width/2+this.horizontalOffset}),a.push({verticalAlign:"bottom",horizontalAlign:"center",top:r.bottom-i.height-this.verticalOffset-(this.noOverlap?r.height:0),left:r.left-n.width/2+r.width/2+this.horizontalOffset})),t&&"middle"!==t||(a.push({verticalAlign:"middle",horizontalAlign:"left",top:r.top-n.height/2+r.height/2+this.verticalOffset,left:r.left+this.horizontalOffset+(this.noOverlap?r.width:0)}),a.push({verticalAlign:"middle",horizontalAlign:"right",top:r.top-n.height/2+r.height/2+this.verticalOffset,left:r.right-i.width-this.horizontalOffset-(this.noOverlap?r.width:0)})),"middle"===t&&"center"===e&&a.push({verticalAlign:"middle",horizontalAlign:"center",top:r.top-n.height/2+r.height/2+this.verticalOffset,left:r.left-n.width/2+r.width/2+this.horizontalOffset});for(l=0;l<a.length;l++){var d=a[l],u=d.verticalAlign===t,f=d.horizontalAlign===e;if(!this.dynamicAlign&&!this.noOverlap&&u&&f){o=d;break}var _=(!t||u)&&(!e||f);if(this.dynamicAlign||_){if(d.offscreenArea=this.__getOffscreenArea(d,i,s),0===d.offscreenArea&&_){o=d;break}o=o||d;var m=d.offscreenArea-o.offscreenArea;(m<0||0===m&&(u||f))&&(o=d)}}return o}};var gr=new Set;const br={properties:{_parentResizable:{type:Object,observer:"_parentResizableChanged"},_notifyingDescendant:{type:Boolean,value:!1}},listeners:{"iron-request-resize-notifications":"_onIronRequestResizeNotifications"},created:function(){this._interestedResizables=[],this._boundNotifyResize=this.notifyResize.bind(this),this._boundOnDescendantIronResize=this._onDescendantIronResize.bind(this)},attached:function(){this._requestResizeNotifications()},detached:function(){this._parentResizable?this._parentResizable.stopResizeNotificationsFor(this):(gr.delete(this),window.removeEventListener("resize",this._boundNotifyResize)),this._parentResizable=null},notifyResize:function(){this.isAttached&&(this._interestedResizables.forEach(function(e){this.resizerShouldNotify(e)&&this._notifyDescendant(e)},this),this._fireResize())},assignParentResizable:function(e){this._parentResizable&&this._parentResizable.stopResizeNotificationsFor(this),this._parentResizable=e,e&&-1===e._interestedResizables.indexOf(this)&&(e._interestedResizables.push(this),e._subscribeIronResize(this))},stopResizeNotificationsFor:function(e){var t=this._interestedResizables.indexOf(e);t>-1&&(this._interestedResizables.splice(t,1),this._unsubscribeIronResize(e))},_subscribeIronResize:function(e){e.addEventListener("iron-resize",this._boundOnDescendantIronResize)},_unsubscribeIronResize:function(e){e.removeEventListener("iron-resize",this._boundOnDescendantIronResize)},resizerShouldNotify:function(e){return!0},_onDescendantIronResize:function(e){this._notifyingDescendant?e.stopPropagation():a||this._fireResize()},_fireResize:function(){this.fire("iron-resize",null,{node:this,bubbles:!1})},_onIronRequestResizeNotifications:function(e){var t=xn(e).rootTarget;t!==this&&(t.assignParentResizable(this),this._notifyDescendant(t),e.stopPropagation())},_parentResizableChanged:function(e){e&&window.removeEventListener("resize",this._boundNotifyResize)},_notifyDescendant:function(e){this.isAttached&&(this._notifyingDescendant=!0,e.notifyResize(),this._notifyingDescendant=!1)},_requestResizeNotifications:function(){if(this.isAttached)if("loading"===document.readyState){var e=this._requestResizeNotifications.bind(this);document.addEventListener("readystatechange",function t(){document.removeEventListener("readystatechange",t),e()})}else this._findParent(),this._parentResizable?this._parentResizable._interestedResizables.forEach(function(e){e!==this&&e._findParent()},this):(gr.forEach(function(e){e!==this&&e._findParent()},this),window.addEventListener("resize",this._boundNotifyResize),this.notifyResize())},_findParent:function(){this.assignParentResizable(null),this.fire("iron-request-resize-notifications",null,{node:this,bubbles:!0,cancelable:!0}),this._parentResizable?gr.delete(this):gr.add(this)}};var vr=Element.prototype,wr=vr.matches||vr.matchesSelector||vr.mozMatchesSelector||vr.msMatchesSelector||vr.oMatchesSelector||vr.webkitMatchesSelector;const Cr={getTabbableNodes:function(e){var t=[];return this._collectTabbableNodes(e,t)?this._sortByTabIndex(t):t},isFocusable:function(e){return wr.call(e,"input, select, textarea, button, object")?wr.call(e,":not([disabled])"):wr.call(e,"a[href], area[href], iframe, [tabindex], [contentEditable]")},isTabbable:function(e){return this.isFocusable(e)&&wr.call(e,':not([tabindex="-1"])')&&this._isVisible(e)},_normalizedTabIndex:function(e){if(this.isFocusable(e)){var t=e.getAttribute("tabindex")||0;return Number(t)}return-1},_collectTabbableNodes:function(e,t){if(e.nodeType!==Node.ELEMENT_NODE||!this._isVisible(e))return!1;var i,n=e,r=this._normalizedTabIndex(n),s=r>0;r>=0&&t.push(n),i="content"===n.localName||"slot"===n.localName?xn(n).getDistributedNodes():xn(n.root||n).children;for(var o=0;o<i.length;o++)s=this._collectTabbableNodes(i[o],t)||s;return s},_isVisible:function(e){var t=e.style;return"hidden"!==t.visibility&&"none"!==t.display&&("hidden"!==(t=window.getComputedStyle(e)).visibility&&"none"!==t.display)},_sortByTabIndex:function(e){var t=e.length;if(t<2)return e;var i=Math.ceil(t/2),n=this._sortByTabIndex(e.slice(0,i)),r=this._sortByTabIndex(e.slice(i));return this._mergeSortByTabIndex(n,r)},_mergeSortByTabIndex:function(e,t){for(var i=[];e.length>0&&t.length>0;)this._hasLowerTabOrder(e[0],t[0])?i.push(t.shift()):i.push(e.shift());return i.concat(e,t)},_hasLowerTabOrder:function(e,t){var i=Math.max(e.tabIndex,0),n=Math.max(t.tabIndex,0);return 0===i||0===n?n>i:i>n}};Mn({_template:We`
    <style>
      :host {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: var(--iron-overlay-backdrop-background-color, #000);
        opacity: 0;
        transition: opacity 0.2s;
        pointer-events: none;
        @apply --iron-overlay-backdrop;
      }

      :host(.opened) {
        opacity: var(--iron-overlay-backdrop-opacity, 0.6);
        pointer-events: auto;
        @apply --iron-overlay-backdrop-opened;
      }
    </style>

    <slot></slot>
`,is:"iron-overlay-backdrop",properties:{opened:{reflectToAttribute:!0,type:Boolean,value:!1,observer:"_openedChanged"}},listeners:{transitionend:"_onTransitionend"},created:function(){this.__openedRaf=null},attached:function(){this.opened&&this._openedChanged(this.opened)},prepare:function(){this.opened&&!this.parentNode&&xn(document.body).appendChild(this)},open:function(){this.opened=!0},close:function(){this.opened=!1},complete:function(){this.opened||this.parentNode!==document.body||xn(this.parentNode).removeChild(this)},_onTransitionend:function(e){e&&e.target===this&&this.complete()},_openedChanged:function(e){if(e)this.prepare();else{var t=window.getComputedStyle(this);"0s"!==t.transitionDuration&&0!=t.opacity||this.complete()}this.isAttached&&(this.__openedRaf&&(window.cancelAnimationFrame(this.__openedRaf),this.__openedRaf=null),this.scrollTop=this.scrollTop,this.__openedRaf=window.requestAnimationFrame(function(){this.__openedRaf=null,this.toggleClass("opened",this.opened)}.bind(this)))}});var xr={"U+0008":"backspace","U+0009":"tab","U+001B":"esc","U+0020":"space","U+007F":"del"},Pr={8:"backspace",9:"tab",13:"enter",27:"esc",33:"pageup",34:"pagedown",35:"end",36:"home",32:"space",37:"left",38:"up",39:"right",40:"down",46:"del",106:"*"},Sr={shift:"shiftKey",ctrl:"ctrlKey",alt:"altKey",meta:"metaKey"},Or=/[a-z0-9*]/,Er=/U\+/,Tr=/^arrow/,Ar=/^space(bar)?/,Nr=/^escape$/;function kr(e,t){var i="";if(e){var n=e.toLowerCase();" "===n||Ar.test(n)?i="space":Nr.test(n)?i="esc":1==n.length?t&&!Or.test(n)||(i=n):i=Tr.test(n)?n.replace("arrow",""):"multiply"==n?"*":n}return i}function Ir(e,t){return e.key?kr(e.key,t):e.detail&&e.detail.key?kr(e.detail.key,t):(i=e.keyIdentifier,n="",i&&(i in xr?n=xr[i]:Er.test(i)?(i=parseInt(i.replace("U+","0x"),16),n=String.fromCharCode(i).toLowerCase()):n=i.toLowerCase()),n||function(e){var t="";return Number(e)&&(t=e>=65&&e<=90?String.fromCharCode(32+e):e>=112&&e<=123?"f"+(e-112+1):e>=48&&e<=57?String(e-48):e>=96&&e<=105?String(e-96):Pr[e]),t}(e.keyCode)||"");var i,n}function Rr(e,t){return Ir(t,e.hasModifiers)===e.key&&(!e.hasModifiers||!!t.shiftKey==!!e.shiftKey&&!!t.ctrlKey==!!e.ctrlKey&&!!t.altKey==!!e.altKey&&!!t.metaKey==!!e.metaKey)}function zr(e){return e.trim().split(" ").map(function(e){return function(e){return 1===e.length?{combo:e,key:e,event:"keydown"}:e.split("+").reduce(function(e,t){var i=t.split(":"),n=i[0],r=i[1];return n in Sr?(e[Sr[n]]=!0,e.hasModifiers=!0):(e.key=n,e.event=r||"keydown"),e},{combo:e.split(":").shift()})}(e)})}Object,Boolean,Array,Object;const Mr=function(e,t){for(var i=zr(t),n=0;n<i.length;++n)if(Rr(i[n],e))return!0;return!1},Lr=function(){this._overlays=[],this._minimumZ=101,this._backdropElement=null,$i(document.documentElement,"tap",function(){}),document.addEventListener("tap",this._onCaptureClick.bind(this),!0),document.addEventListener("focus",this._onCaptureFocus.bind(this),!0),document.addEventListener("keydown",this._onCaptureKeyDown.bind(this),!0)};Lr.prototype={constructor:Lr,get backdropElement(){return this._backdropElement||(this._backdropElement=document.createElement("iron-overlay-backdrop")),this._backdropElement},get deepActiveElement(){var e=document.activeElement;for(e&&e instanceof Element!=!1||(e=document.body);e.root&&xn(e.root).activeElement;)e=xn(e.root).activeElement;return e},_bringOverlayAtIndexToFront:function(e){var t=this._overlays[e];if(t){var i=this._overlays.length-1,n=this._overlays[i];if(n&&this._shouldBeBehindOverlay(t,n)&&i--,!(e>=i)){var r=Math.max(this.currentOverlayZ(),this._minimumZ);for(this._getZ(t)<=r&&this._applyOverlayZ(t,r);e<i;)this._overlays[e]=this._overlays[e+1],e++;this._overlays[i]=t}}},addOrRemoveOverlay:function(e){e.opened?this.addOverlay(e):this.removeOverlay(e)},addOverlay:function(e){var t=this._overlays.indexOf(e);if(t>=0)return this._bringOverlayAtIndexToFront(t),void this.trackBackdrop();var i=this._overlays.length,n=this._overlays[i-1],r=Math.max(this._getZ(n),this._minimumZ),s=this._getZ(e);if(n&&this._shouldBeBehindOverlay(e,n)){this._applyOverlayZ(n,r),i--;var o=this._overlays[i-1];r=Math.max(this._getZ(o),this._minimumZ)}s<=r&&this._applyOverlayZ(e,r),this._overlays.splice(i,0,e),this.trackBackdrop()},removeOverlay:function(e){var t=this._overlays.indexOf(e);-1!==t&&(this._overlays.splice(t,1),this.trackBackdrop())},currentOverlay:function(){var e=this._overlays.length-1;return this._overlays[e]},currentOverlayZ:function(){return this._getZ(this.currentOverlay())},ensureMinimumZ:function(e){this._minimumZ=Math.max(this._minimumZ,e)},focusOverlay:function(){var e=this.currentOverlay();e&&e._applyFocus()},trackBackdrop:function(){var e=this._overlayWithBackdrop();(e||this._backdropElement)&&(this.backdropElement.style.zIndex=this._getZ(e)-1,this.backdropElement.opened=!!e,this.backdropElement.prepare())},getBackdrops:function(){for(var e=[],t=0;t<this._overlays.length;t++)this._overlays[t].withBackdrop&&e.push(this._overlays[t]);return e},backdropZ:function(){return this._getZ(this._overlayWithBackdrop())-1},_overlayWithBackdrop:function(){for(var e=this._overlays.length-1;e>=0;e--)if(this._overlays[e].withBackdrop)return this._overlays[e]},_getZ:function(e){var t=this._minimumZ;if(e){var i=Number(e.style.zIndex||window.getComputedStyle(e).zIndex);i==i&&(t=i)}return t},_setZ:function(e,t){e.style.zIndex=t},_applyOverlayZ:function(e,t){this._setZ(e,t+2)},_overlayInPath:function(e){e=e||[];for(var t=0;t<e.length;t++)if(e[t]._manager===this)return e[t]},_onCaptureClick:function(e){var t=this._overlays.length-1;if(-1!==t)for(var i,n=xn(e).path;(i=this._overlays[t])&&this._overlayInPath(n)!==i&&(i._onCaptureClick(e),i.allowClickThrough);)t--},_onCaptureFocus:function(e){var t=this.currentOverlay();t&&t._onCaptureFocus(e)},_onCaptureKeyDown:function(e){var t=this.currentOverlay();t&&(Mr(e,"esc")?t._onCaptureEsc(e):Mr(e,"tab")&&t._onCaptureTab(e))},_shouldBeBehindOverlay:function(e,t){return!e.alwaysOnTop&&t.alwaysOnTop}};const Dr=new Lr;var Fr,Br,Hr={pageX:0,pageY:0},jr=null,$r=[],qr=["wheel","mousewheel","DOMMouseScroll","touchstart","touchmove"];function Yr(e){Vr.indexOf(e)>=0||(0===Vr.length&&function(){Fr=Fr||function(e){e.cancelable&&function(e){var t=xn(e).rootTarget;"touchmove"!==e.type&&jr!==t&&(jr=t,$r=function(e){for(var t=[],i=e.indexOf(Br),n=0;n<=i;n++)if(e[n].nodeType===Node.ELEMENT_NODE){var r=e[n],s=r.style;"scroll"!==s.overflow&&"auto"!==s.overflow&&(s=window.getComputedStyle(r)),"scroll"!==s.overflow&&"auto"!==s.overflow||t.push(r)}return t}(xn(e).path));if(!$r.length)return!0;if("touchstart"===e.type)return!1;var i=function(e){var t={deltaX:e.deltaX,deltaY:e.deltaY};if("deltaX"in e);else if("wheelDeltaX"in e&&"wheelDeltaY"in e)t.deltaX=-e.wheelDeltaX,t.deltaY=-e.wheelDeltaY;else if("wheelDelta"in e)t.deltaX=0,t.deltaY=-e.wheelDelta;else if("axis"in e)t.deltaX=1===e.axis?e.detail:0,t.deltaY=2===e.axis?e.detail:0;else if(e.targetTouches){var i=e.targetTouches[0];t.deltaX=Hr.pageX-i.pageX,t.deltaY=Hr.pageY-i.pageY}return t}(e);return!function(e,t,i){if(!t&&!i)return;for(var n=Math.abs(i)>=Math.abs(t),r=0;r<e.length;r++){var s=e[r];if(n?i<0?s.scrollTop>0:s.scrollTop<s.scrollHeight-s.clientHeight:t<0?s.scrollLeft>0:s.scrollLeft<s.scrollWidth-s.clientWidth)return s}}($r,i.deltaX,i.deltaY)}(e)&&e.preventDefault();if(e.targetTouches){var t=e.targetTouches[0];Hr.pageX=t.pageX,Hr.pageY=t.pageY}}.bind(void 0);for(var e=0,t=qr.length;e<t;e++)document.addEventListener(qr[e],Fr,{capture:!0,passive:!1})}(),Vr.push(e),Br=Vr[Vr.length-1])}function Ur(e){var t=Vr.indexOf(e);-1!==t&&(Vr.splice(t,1),Br=Vr[Vr.length-1],0===Vr.length&&function(){for(var e=0,t=qr.length;e<t;e++)document.removeEventListener(qr[e],Fr,{capture:!0,passive:!1})}())}const Vr=[];const Xr={properties:{opened:{observer:"_openedChanged",type:Boolean,value:!1,notify:!0},canceled:{observer:"_canceledChanged",readOnly:!0,type:Boolean,value:!1},withBackdrop:{observer:"_withBackdropChanged",type:Boolean},noAutoFocus:{type:Boolean,value:!1},noCancelOnEscKey:{type:Boolean,value:!1},noCancelOnOutsideClick:{type:Boolean,value:!1},closingReason:{type:Object},restoreFocusOnClose:{type:Boolean,value:!1},allowClickThrough:{type:Boolean},alwaysOnTop:{type:Boolean},scrollAction:{type:String},_manager:{type:Object,value:Dr},_focusedChild:{type:Object}},listeners:{"iron-resize":"_onIronResize"},observers:["__updateScrollObservers(isAttached, opened, scrollAction)"],get backdropElement(){return this._manager.backdropElement},get _focusNode(){return this._focusedChild||xn(this).querySelector("[autofocus]")||this},get _focusableNodes(){return Cr.getTabbableNodes(this)},ready:function(){this.__isAnimating=!1,this.__shouldRemoveTabIndex=!1,this.__firstFocusableNode=this.__lastFocusableNode=null,this.__rafs={},this.__restoreFocusNode=null,this.__scrollTop=this.__scrollLeft=null,this.__onCaptureScroll=this.__onCaptureScroll.bind(this),this.__rootNodes=null,this._ensureSetup()},attached:function(){this.opened&&this._openedChanged(this.opened),this._observer=xn(this).observeNodes(this._onNodesChange)},detached:function(){for(var e in xn(this).unobserveNodes(this._observer),this._observer=null,this.__rafs)null!==this.__rafs[e]&&cancelAnimationFrame(this.__rafs[e]);this.__rafs={},this._manager.removeOverlay(this),this.__isAnimating&&(this.opened?this._finishRenderOpened():(this._applyFocus(),this._finishRenderClosed()))},toggle:function(){this._setCanceled(!1),this.opened=!this.opened},open:function(){this._setCanceled(!1),this.opened=!0},close:function(){this._setCanceled(!1),this.opened=!1},cancel:function(e){this.fire("iron-overlay-canceled",e,{cancelable:!0}).defaultPrevented||(this._setCanceled(!0),this.opened=!1)},invalidateTabbables:function(){this.__firstFocusableNode=this.__lastFocusableNode=null},_ensureSetup:function(){this._overlaySetup||(this._overlaySetup=!0,this.style.outline="none",this.style.display="none")},_openedChanged:function(e){e?this.removeAttribute("aria-hidden"):this.setAttribute("aria-hidden","true"),this.isAttached&&(this.__isAnimating=!0,this.__deraf("__openedChanged",this.__openedChanged))},_canceledChanged:function(){this.closingReason=this.closingReason||{},this.closingReason.canceled=this.canceled},_withBackdropChanged:function(){this.withBackdrop&&!this.hasAttribute("tabindex")?(this.setAttribute("tabindex","-1"),this.__shouldRemoveTabIndex=!0):this.__shouldRemoveTabIndex&&(this.removeAttribute("tabindex"),this.__shouldRemoveTabIndex=!1),this.opened&&this.isAttached&&this._manager.trackBackdrop()},_prepareRenderOpened:function(){this.__restoreFocusNode=this._manager.deepActiveElement,this._preparePositioning(),this.refit(),this._finishPositioning(),this.noAutoFocus&&document.activeElement===this._focusNode&&(this._focusNode.blur(),this.__restoreFocusNode.focus())},_renderOpened:function(){this._finishRenderOpened()},_renderClosed:function(){this._finishRenderClosed()},_finishRenderOpened:function(){this.notifyResize(),this.__isAnimating=!1,this.fire("iron-overlay-opened")},_finishRenderClosed:function(){this.style.display="none",this.style.zIndex="",this.notifyResize(),this.__isAnimating=!1,this.fire("iron-overlay-closed",this.closingReason)},_preparePositioning:function(){this.style.transition=this.style.webkitTransition="none",this.style.transform=this.style.webkitTransform="none",this.style.display=""},_finishPositioning:function(){this.style.display="none",this.scrollTop=this.scrollTop,this.style.transition=this.style.webkitTransition="",this.style.transform=this.style.webkitTransform="",this.style.display="",this.scrollTop=this.scrollTop},_applyFocus:function(){if(this.opened)this.noAutoFocus||this._focusNode.focus();else{if(this.restoreFocusOnClose&&this.__restoreFocusNode){var e=this._manager.deepActiveElement;(e===document.body||xn(this).deepContains(e))&&this.__restoreFocusNode.focus()}this.__restoreFocusNode=null,this._focusNode.blur(),this._focusedChild=null}},_onCaptureClick:function(e){this.noCancelOnOutsideClick||this.cancel(e)},_onCaptureFocus:function(e){if(this.withBackdrop){var t=xn(e).path;-1===t.indexOf(this)?(e.stopPropagation(),this._applyFocus()):this._focusedChild=t[0]}},_onCaptureEsc:function(e){this.noCancelOnEscKey||this.cancel(e)},_onCaptureTab:function(e){if(this.withBackdrop){this.__ensureFirstLastFocusables();var t=e.shiftKey,i=t?this.__firstFocusableNode:this.__lastFocusableNode,n=t?this.__lastFocusableNode:this.__firstFocusableNode,r=!1;if(i===n)r=!0;else{var s=this._manager.deepActiveElement;r=s===i||s===this}r&&(e.preventDefault(),this._focusedChild=n,this._applyFocus())}},_onIronResize:function(){this.opened&&!this.__isAnimating&&this.__deraf("refit",this.refit)},_onNodesChange:function(){this.opened&&!this.__isAnimating&&(this.invalidateTabbables(),this.notifyResize())},__ensureFirstLastFocusables:function(){var e=this._focusableNodes;this.__firstFocusableNode=e[0],this.__lastFocusableNode=e[e.length-1]},__openedChanged:function(){this.opened?(this._prepareRenderOpened(),this._manager.addOverlay(this),this._applyFocus(),this._renderOpened()):(this._manager.removeOverlay(this),this._applyFocus(),this._renderClosed())},__deraf:function(e,t){var i=this.__rafs;null!==i[e]&&cancelAnimationFrame(i[e]),i[e]=requestAnimationFrame(function(){i[e]=null,t.call(this)}.bind(this))},__updateScrollObservers:function(e,t,i){e&&t&&this.__isValidScrollAction(i)?("lock"===i&&(this.__saveScrollPosition(),Yr(this)),this.__addScrollListeners()):(Ur(this),this.__removeScrollListeners())},__addScrollListeners:function(){if(!this.__rootNodes){if(this.__rootNodes=[],a)for(var e=this;e;)e.nodeType===Node.DOCUMENT_FRAGMENT_NODE&&e.host&&this.__rootNodes.push(e),e=e.host||e.assignedSlot||e.parentNode;this.__rootNodes.push(document)}this.__rootNodes.forEach(function(e){e.addEventListener("scroll",this.__onCaptureScroll,{capture:!0,passive:!0})},this)},__removeScrollListeners:function(){this.__rootNodes&&this.__rootNodes.forEach(function(e){e.removeEventListener("scroll",this.__onCaptureScroll,{capture:!0,passive:!0})},this),this.isAttached||(this.__rootNodes=null)},__isValidScrollAction:function(e){return"lock"===e||"refit"===e||"cancel"===e},__onCaptureScroll:function(e){if(!(this.__isAnimating||xn(e).path.indexOf(this)>=0))switch(this.scrollAction){case"lock":this.__restoreScrollPosition();break;case"refit":this.__deraf("refit",this.refit);break;case"cancel":this.cancel(e)}},__saveScrollPosition:function(){document.scrollingElement?(this.__scrollTop=document.scrollingElement.scrollTop,this.__scrollLeft=document.scrollingElement.scrollLeft):(this.__scrollTop=Math.max(document.documentElement.scrollTop,document.body.scrollTop),this.__scrollLeft=Math.max(document.documentElement.scrollLeft,document.body.scrollLeft))},__restoreScrollPosition:function(){document.scrollingElement?(document.scrollingElement.scrollTop=this.__scrollTop,document.scrollingElement.scrollLeft=this.__scrollLeft):(document.documentElement.scrollTop=document.body.scrollTop=this.__scrollTop,document.documentElement.scrollLeft=document.body.scrollLeft=this.__scrollLeft)}},Jr={hostAttributes:{role:"dialog",tabindex:"-1"},properties:{modal:{type:Boolean,value:!1},__readied:{type:Boolean,value:!1}},observers:["_modalChanged(modal, __readied)"],listeners:{tap:"_onDialogClick"},ready:function(){this.__prevNoCancelOnOutsideClick=this.noCancelOnOutsideClick,this.__prevNoCancelOnEscKey=this.noCancelOnEscKey,this.__prevWithBackdrop=this.withBackdrop,this.__readied=!0},_modalChanged:function(e,t){t&&(e?(this.__prevNoCancelOnOutsideClick=this.noCancelOnOutsideClick,this.__prevNoCancelOnEscKey=this.noCancelOnEscKey,this.__prevWithBackdrop=this.withBackdrop,this.noCancelOnOutsideClick=!0,this.noCancelOnEscKey=!0,this.withBackdrop=!0):(this.noCancelOnOutsideClick=this.noCancelOnOutsideClick&&this.__prevNoCancelOnOutsideClick,this.noCancelOnEscKey=this.noCancelOnEscKey&&this.__prevNoCancelOnEscKey,this.withBackdrop=this.withBackdrop&&this.__prevWithBackdrop))},_updateClosingReasonConfirmed:function(e){this.closingReason=this.closingReason||{},this.closingReason.confirmed=e},_onDialogClick:function(e){for(var t=xn(e).path,i=0,n=t.indexOf(this);i<n;i++){var r=t[i];if(r.hasAttribute&&(r.hasAttribute("dialog-dismiss")||r.hasAttribute("dialog-confirm"))){this._updateClosingReasonConfirmed(r.hasAttribute("dialog-confirm")),this.close(),e.stopPropagation();break}}}};Mn({_template:We`
    <style include="paper-dialog-shared-styles"></style>
    <slot></slot>
`,is:"paper-dialog",behaviors:[[[yr,br,Xr],Jr],mr],listeners:{"neon-animation-finish":"_onNeonAnimationFinish"},_renderOpened:function(){this.cancelAnimation(),this.playAnimation("entry")},_renderClosed:function(){this.cancelAnimation(),this.playAnimation("exit")},_onNeonAnimationFinish:function(){this.opened?this._finishRenderOpened():this._finishRenderClosed()}});customElements.define("hacs-repository",class extends Ze{static get template(){return We`
      <paper-dialog>
        <h2>Content</h2>
      </paper-dialog>
    `}});
