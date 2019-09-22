import {
  LitElement,
  customElement,
  CSSResult,
  TemplateResult,
  html,
  css
} from "lit-element";

import "./HacsCard"
import "./HacsHeader"
import { HomeAssistantObject } from './HomeAssistantObject'

@customElement("hacs-frontend")
class BoilerplateCard extends LitElement {
  public hass = (parent.document.querySelector('home-assistant') as HomeAssistantObject).hass;

  protected render(): TemplateResult | void {

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
      <hacs-header></hacs-header>
      <div class="hacs-content">
          <hacs-overview-card
          header="${this.hass.localize("component.hacs.config.title")}"
          content="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed posuere tincidunt libero, quis imperdiet ex tincidunt eget. Phasellus auctor sit amet ligula ut malesuada.">
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
            background-color: #fce588;
            padding: 8px;
          }
        `;
  }
}