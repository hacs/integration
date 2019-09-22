import {
  LitElement,
  html,
  customElement,
  CSSResult,
  TemplateResult,
  css
} from "lit-element";

import { HacsCard } from "./HacsCard"
import "./Header"
import { HomeAssistantObject } from './HomeAssistantObject'


customElements.define('hacs-overview-card', HacsCard);
// TODO Name your custom element
@customElement("boilerplate-card")
class BoilerplateCard extends LitElement {
  public hass = (parent.document.querySelector('home-assistant') as HomeAssistantObject).hass;

  protected render(): TemplateResult | void {

    // TODO Check for stateObj or other necessary things and render a warning if missing
    return html`
    <script>document.getElementsByTagName("html").item(0).setAttribute("style", parent.document.getElementsByTagName("html").item(0).style.cssText)</script>
    <hacs-header></hacs-header>
    <div content>
          <hacs-overview-card
          header="${this.hass.localize("component.hacs.config.title")}"
          >content</hacs-overview-card>
          <ha-card>
          <div class="warning">Show Warning</div>
        </ha-card>
        </div>
        `;
  }

  static get styles(): CSSResult {
    return css`
          .warning {
            display: block;
            color: black;
            background-color: #fce588;
            padding: 8px;
          }
        `;
  }
}