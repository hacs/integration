import{_ as i,n as e,r as o,e as t,t as s,s as d,x as n,T as r,c as a}from"./matter-dashboard-app-Bs2zeWCY.js";import{c as l,f as m}from"./fire_event-D4wM1ZZB.js";import"./prevent_default-dFwBPK3O.js";let c=class extends d{constructor(){super(...arguments),this._loading=!1}render(){return n`<md-outlined-text-field label="Share code" .disabled="${this._loading}">
      </md-outlined-text-field>
      <br />
      <br />
      <md-outlined-button @click=${this._commissionNode} .disabled="${this._loading}"
        >Commission</md-outlined-button
      >${this._loading?n`<md-circular-progress indeterminate></md-circular-progress>`:r}`}async _commissionNode(){this._loading=!0;try{const i=await this.client.commissionWithCode(this._pairingCodeField.value,!0);m(this,"node-commissioned",i)}catch(i){alert(`Error commissioning node: ${i.message}`)}finally{this._loading=!1}}};i([l({context:a,subscribe:!0}),e({attribute:!1})],c.prototype,"client",void 0),i([o()],c.prototype,"_loading",void 0),i([t("md-outlined-text-field[label='Share code']")],c.prototype,"_pairingCodeField",void 0),c=i([s("commission-node-existing")],c);export{c as CommissionNodeExisting};
