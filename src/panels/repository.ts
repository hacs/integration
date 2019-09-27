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

import { Configuration, Repositories } from "../types"

@customElement("hacs-panel-repository")
export class HacsPanelRepository extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repositories;

  @property()
  public configuration!: Configuration;

  @property()
  public repository!: string;

  render(): TemplateResult | void {
    var _repository = this.repository;
    var _repositories = this.repositories.content || [];
    _repositories = this.repositories.content.filter(function (repo) {
      return repo.id === _repository
    });
    var repo = _repositories[0]
    return html`

    <ha-card header="${repo.name}">
      <div class="card content">
      </div>
    </ha-card>
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