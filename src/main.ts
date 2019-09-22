import {
  LitElement,
  customElement,
  CSSResult,
  TemplateResult,
  html,
  css,
  property,
  PropertyValues
} from "lit-element";

import {
  HomeAssistant,
  handleClick,
  longPress,
  hasConfigOrEntityChanged
} from "custom-card-helpers";

import "./HacsCard"
//import "./HacsHeader"
import { HomeAssistantObject } from './HomeAssistantObject'

class WsHacsConfigResponse {
  public content = null;
}

@customElement("hacs-frontend")
class HacsFrontendBase extends LitElement {
  @property() public wsResponse?: WsHacsConfigResponse;
  public hass = (parent.document.querySelector('home-assistant') as HomeAssistantObject).hass;

  protected shouldUpdate(changedProps: PropertyValues): boolean {
    this.render()
    return hasConfigOrEntityChanged(this, changedProps, true);
  }

  protected getHacsConfig(hass) {
    hass.connection.sendMessagePromise({
      type: 'hacs/config'
    }).then(
      (resp) => {
        console.log('Message success!', resp);
        this.wsResponse = resp.content;
        this.render()
      },
      (err) => {
        console.error('Message failed!', err);
      }
    );
  }

  protected render(): TemplateResult | void {
    if (this.wsResponse !== undefined) this.getHacsConfig(this.hass);
    return html`
    <html>
    <head>
      <script src="/hacs_experimental/hacs.js"></script>
      <script src="/hacs_experimental/hacs.css"></script>
      <link rel="stylesheet" href="/hacs_experimental/materialize.min.css.gz">
      <script src="/hacs_experimental/materialize.min.js.gz"></script>

      <script>
        document.getElementsByTagName("html").item(0).setAttribute("style", parent.document.getElementsByTagName("html").item(0).style.cssText)
      </script>
    </head>
    <body>
    <div class="navbar-fixed" >
    <nav class="nav-extended hacs-nav" >
      <div class="nav-content" >
        <ul class="right tabs tabs-transparent" >
          <li class="tab {{ 'active' if location == 'overview' }}" > <a
          href="/hacsweb/{{ hacs.token }}/overview?timestamp={{ timestamp }}" >
      ${ this.hass.localize("component.hacs.common.overview")} </a></li >
        <li class="tab {{ 'active' if location == 'store' }}" > <a
                href="/hacsweb/{{ hacs.token }}/store?timestamp={{ timestamp }}" >
      ${ this.hass.localize("component.hacs.common.store")} </a></li >
        <li class="tab right {{ 'active' if location == 'settings' }}" > <a
                href="/hacsweb/{{ hacs.token }}/settings?timestamp={{ timestamp }}" >
      ${ this.hass.localize("component.hacs.common.settings")} </a></li >
        </ul>
        </div>
        </nav>
        </div>
      <div class="hacs-content">
          <hacs-overview-card
          header="${this.hass.localize("component.hacs.config.title")}"
          content="${this.wsResponse} Lorem ipsum dolor sit amet, consectetur adipiscing elit.Sed posuere tincidunt libero, quis imperdiet ex tincidunt eget.Phasellus auctor sit amet ligula ut malesuada.">
    </hacs-overview-card>
      </div>
      </body>
      </html>
        `;
  }

  static get styles(): CSSResult {
    return css`
        .warning {
          display: block;
          color: black;
          background - color: #fce588;
          padding: 8px;
        }`;
  }
}