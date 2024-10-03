import{_ as t,n as e,t as o,s as i,x as s}from"./matter-dashboard-app-Bs2zeWCY.js";import{p as l}from"./prevent_default-dFwBPK3O.js";let d=class extends i{render(){const t=this.params;return s`
      <md-dialog open @cancel=${l} @closed=${this._handleClosed}>
        ${t.title?s`<div slot="headline">${t.title}</div>`:""}
        ${t.text?s`<div slot="content">${t.text}</div>`:""}
        <div slot="actions">
          ${"prompt"===this.type?s`
                <md-text-button @click=${this._cancel}>
                  ${t.cancelText||"Cancel"}
                </md-text-button>
              `:""}
          <md-text-button @click=${this._confirm}>
            ${t.confirmText||"OK"}
          </md-text-button>
        </div>
      </md-dialog>
    `}_cancel(){this._setResult(!1)}_confirm(){this._setResult(!0)}_setResult(t){this.dialogResult(t),this.shadowRoot.querySelector("md-dialog").close()}_handleClosed(){this.parentElement.removeChild(this)}};t([e({attribute:!1})],d.prototype,"params",void 0),t([e({attribute:!1})],d.prototype,"dialogResult",void 0),t([e()],d.prototype,"type",void 0),d=t([o("dialox-box")],d);export{d as DialogBox};
