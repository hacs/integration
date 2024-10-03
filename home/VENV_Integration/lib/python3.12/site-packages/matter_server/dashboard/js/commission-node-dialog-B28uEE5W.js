import{_ as i,n as o,r as e,t as s,s as t,x as d}from"./matter-dashboard-app-Bs2zeWCY.js";import{p as n}from"./prevent_default-dFwBPK3O.js";let m=class extends t{render(){return d`
      <md-dialog open @cancel=${n} @closed=${this._handleClosed}>
        <div slot="headline">Commission node</div>
        <div slot="content" @node-commissioned=${this._nodeCommissioned}>
          ${this._mode?"wifi"===this._mode?d`<commission-node-wifi></commission-node-wifi>`:"thread"===this._mode?d`<commission-node-thread></commission-node-thread>`:d`<commission-node-existing></commission-node-existing>`:d`<md-list>
                <md-list-item type="button" .disabled=${!this.client.serverInfo.bluetooth_enabled} @click=${this._commissionWifi}
                  >Commission new WiFi device</md-list-item
                >
                <md-list-item type="button" .disabled=${!this.client.serverInfo.bluetooth_enabled} @click=${this._commissionThread}
                  >Commission new Thread device</md-list-item
                >
                <md-list-item type="button" @click=${this._commissionExisting}
                  >Commission existing device</md-list-item
                >
              </md-list>`}
        </div>
        <div slot="actions">
          <md-text-button @click=${this._close}>Cancel</md-text-button>
        </div>
      </md-dialog>
    `}_commissionWifi(){this.client.serverInfo.bluetooth_enabled&&(import("./commission-node-wifi-Cbzc29xE.js"),this._mode="wifi")}_commissionThread(){this.client.serverInfo.bluetooth_enabled&&(import("./commission-node-thread-B9QQNxOA.js"),this._mode="thread")}_commissionExisting(){import("./commission-node-existing-C5hLXGeR.js"),this._mode="existing"}_nodeCommissioned(i){window.location.href=`#node/${i.detail.node_id}`,this._close()}_close(){this.shadowRoot.querySelector("md-dialog").close()}_handleClosed(){this.parentNode.removeChild(this)}};i([o({attribute:!1})],m.prototype,"client",void 0),i([e()],m.prototype,"_mode",void 0),m=i([s("commission-node-dialog")],m);export{m as ComissionNodeDialog};
