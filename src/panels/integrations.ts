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

@customElement("hacs-panel-integrations")
export class HacsPanelIntegrations extends LitElement {

  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories;

  @property()
  public panel!: string;

  protected render(): TemplateResult | void {
    return html`
    <div class="hacs-repositories">
    ${this.repositories.map(repo =>
      html`<ha-card header="${repo.name}">
      <div class="card-content">
        <i>${repo.description}<i>
      </div>
      </ha-card>
      `)}
    </div>
          `;
  }

  static get styles(): CSSResult {
    return css`
      :host {
        color: var(--primary-text-color);
      }
      ha-card {
        margin: 8px;
      }
      `;
  }
}