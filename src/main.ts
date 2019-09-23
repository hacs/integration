import {
  LitElement,
  customElement,
  CSSResult,
  TemplateResult,
  html,
  css,
  property
} from "lit-element";

import {
  HomeAssistant
} from "custom-card-helpers";

import "@granite-elements/granite-spinner";

import { load_lovelace } from "./FromCardTools"


interface WebSocketResponse {
  content?: string;
}

@customElement("hacs-frontend")
class HacsFrontendBase extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public narrow!: boolean;

  @property()
  public wsResponse?: WebSocketResponse;

  firstUpdated() {
    console.log("loaded");
    this.requestUpdate()
    this.hass.connection.sendMessagePromise({
      type: "hacs/config"
    }).then(
      (resp) => {
        this.wsResponse = resp as WebSocketResponse;
        console.log(load_lovelace())
        console.log('Message OK!', resp);
      },
      (err) => {
        console.error('Message failed!', err);
      }
    );
  }

  unReachable() {
    //let pm = Pacman;
  }


  updated(changedProperties: any) {
    console.log('updated');
    changedProperties.forEach((oldValue: any, propName: any, newValue: any) => {
      console.log(`${propName} changed. oldValue: ${oldValue}, newValue: ${newValue}`);
    });
  }

  protected render(): TemplateResult | void {
    if (this.wsResponse === undefined) return html`<granite-spinner active hover size=400 containerHeight=100%></granite-spinner>`
    return html`

    <app-header-layout has-scrolling-region>
    <app-header slot="header" fixed>
      <app-toolbar>
        <ha-menu-button .hass="${this.hass}" .narrow="${this.narrow}"></ha-menu-button>
        <div main-title>${this.hass.localize("component.hacs.config.title")}</div>
      </app-toolbar>
    </app-header>





      <div class="hacs-content">
          <ha-card header="(This is a ha-card element)${this.hass.localize("component.hacs.config.title")}">
          <div class="card-content">
          ${this.wsResponse.content} Lorem ipsum dolor sit amet, consectetur adipiscing elit.Sed posuere tincidunt libero, quis imperdiet ex tincidunt eget.Phasellus auctor sit amet ligula ut malesuada.
          </div>
          </ha-card>
      </div>




  </app-header-layout>
        `;
  }

  static get styles(): CSSResult {
    return css`
    app-header {
      color: var(--text-primary-color);
      background-color: var(--primary-color);
      font-weight: 400;
    }
    `;
  }
}