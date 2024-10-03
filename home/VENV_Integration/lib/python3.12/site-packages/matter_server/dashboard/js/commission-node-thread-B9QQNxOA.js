import{_ as t,n as e,r as i,e as d,t as a,s,x as o,T as r,c as l}from"./matter-dashboard-app-Bs2zeWCY.js";import{c as n,f as c}from"./fire_event-D4wM1ZZB.js";import"./prevent_default-dFwBPK3O.js";let m=class extends s{constructor(){super(...arguments),this._loading=!1}render(){return this.client.serverInfo.thread_credentials_set?o`<md-outlined-text-field label="Pairing code" .disabled="${this._loading}">
      </md-outlined-text-field>
      <br />
      <br />
      <md-outlined-button @click=${this._commissionNode} .disabled="${this._loading}"
        >Commission</md-outlined-button
      >${this._loading?o`<md-circular-progress indeterminate></md-circular-progress>`:r}`:o`<md-outlined-text-field label="Thread dataset" .disabled="${this._loading}">
        </md-outlined-text-field>
        <br />
        <br />
        <md-outlined-button @click=${this._setThreadDataset} .disabled="${this._loading}"
          >Set Thread Dataset</md-outlined-button
        >${this._loading?o`<md-circular-progress indeterminate></md-circular-progress>`:r}`}async _setThreadDataset(){const t=this._datasetField.value;if(t){this._loading=!0;try{await this.client.setThreadOperationalDataset(t)}catch(t){alert(`Error setting Thread dataset: ${t.message}`)}finally{this._loading=!1}}else alert("Dataset is required")}async _commissionNode(){this._loading=!0;try{const t=await this.client.commissionWithCode(this._pairingCodeField.value,!1);c(this,"node-commissioned",t)}catch(t){alert(`Error commissioning node: ${t.message}`)}finally{this._loading=!1}}};t([n({context:l,subscribe:!0}),e({attribute:!1})],m.prototype,"client",void 0),t([i()],m.prototype,"_loading",void 0),t([d("md-outlined-text-field[label='Thread dataset']")],m.prototype,"_datasetField",void 0),t([d("md-outlined-text-field[label='Pairing code']")],m.prototype,"_pairingCodeField",void 0),m=t([a("commission-node-thread")],m);export{m as CommissionNodeThread};
