import {
  customElement,
  LitElement,
  TemplateResult,
  html,
} from "lit-element";

import { HomeAssistantObject } from './HomeAssistantObject'

@customElement("hacs-header")
class HacsHeader extends LitElement {
  public hass = (parent.document.querySelector('home-assistant') as HomeAssistantObject).hass;

  protected render(): TemplateResult | void {
    return html`
    <link rel="stylesheet" href="/hacs_experimental/materialize.min.css.gz">
    <script src="/hacs_experimental/materialize.min.js.gz"></script>
    <script src="/hacs_experimental/hacs.js"></script>
    <script src="/hacs_experimental/hacs.css"></script>
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
      </div>`;
  }

}