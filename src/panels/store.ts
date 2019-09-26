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

@customElement("hacs-panel-store")
export class HacsPanelStore extends LitElement {

  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories;

  @property()
  public panel;

  protected render(): TemplateResult | void {
    const category = this.panel;
    var _repositories = this.repositories.content || [];
    _repositories = this.repositories.content.filter(function (repo) {
      return repo.category === category;
    });

    return html`
    <div class="hacs-repositories">
    ${_repositories.map(repo =>
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