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
import "../repositoryView"
import { navigate } from "../navigate"

@customElement("hacs-panel")
export class HacsPanelStore extends LitElement {

  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repositories

  @property()
  public configuration!: Configuration

  @property()
  public panel;

  @property()
  public repository_view = false;

  @property()
  public repository: string;

  private getRepositories(): void {
    this.hass.connection.sendMessagePromise({
      type: "hacs/config"
    }).then(
      (resp) => {
        this.configuration = resp;
      },
      (err) => {
        console.error('Message failed!', err);
      }
    )
    this.hass.connection.sendMessagePromise({
      type: "hacs/repositories"
    }).then(
      (resp) => {
        this.repositories = resp;
      },
      (err) => {
        console.error('Message failed!', err);
      }
    )
    this.requestUpdate();
  };


  protected render(): TemplateResult | void {
    if (this.panel === "repository") {
      // How fun, this is a repository!
      console.log("REPO", this.repository)
      return html`
      <hacs-panel-repository
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .repository=${this.repository}
      on-change
      >
      </hacs-panel-repository>`
    } else {

      const category = this.panel;
      const config = this.configuration
      var _repositories = this.repositories.content || [];
      _repositories = this.repositories.content.filter(function (repo) {

        if (category !== "installed") {
          // Hide HACS from the store
          if (repo.id === "172733314") return false;

          // Hide hidden repos from the store
          if (repo.hide) return false;

          // Check contry restrictions
          if (config.country !== null) {
            if (config.country !== repo.country) return false;
          }

        } else {
          if (repo.installed) return true;
        }

        // Object looks OK, let's show it
        if (repo.category === category) return true;

        // Fallback to not showing it.
        return false
      });

      return html`
    <div class="card-group">
    ${_repositories.sort((a, b) => (a.name > b.name) ? 1 : -1).map(repo =>
        html`

      <paper-card id="${repo.id}" @click="${this.ShowRepository}" .RepoID="${repo.id}">
      <div class="card-content">
        <div>
          <ha-icon icon="mdi:cube" class="repo-state-${repo.installed}" title="Add-on is running"></ha-icon>
          <div>
            <div class="title">${repo.name}</div>
            <div class="addition">${repo.description}</div>
          </div>
        </div>
      </div>
      </paper-card>
      `)}
    </div>
          `;
    }
  }

  ShowRepository(ev) {
    ev.path.forEach((item) => {
      if (item.RepoID !== undefined) {
        this.panel = `repository`;
        this.repository = item.RepoID;
        this.repository_view = true;
        this.requestUpdate();
        navigate(this, `/hacs/repository/${item.RepoID}`);

      }
    })
  }

  static get styles(): CSSResult {
    return css`
    :host {
      font-family: var(--paper-font-body1_-_font-family); -webkit-font-smoothing: var(--paper-font-body1_-_-webkit-font-smoothing); font-size: var(--paper-font-body1_-_font-size); font-weight: var(--paper-font-body1_-_font-weight); line-height: var(--paper-font-body1_-_line-height);
    }

    app-header-layout, ha-app-layout {
      background-color: var(--primary-background-color);
    }

    app-header, app-toolbar, paper-tabs {
      background-color: var(--primary-color);
        font-weight: 400;
        text-transform: uppercase;
        color: var(--text-primary-color, white);
    }

    app-toolbar ha-menu-button + [main-title], app-toolbar ha-paper-icon-button-arrow-prev + [main-title], app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }

    h1 {
      font-family: var(--paper-font-title_-_font-family); -webkit-font-smoothing: var(--paper-font-title_-_-webkit-font-smoothing); white-space: var(--paper-font-title_-_white-space); overflow: var(--paper-font-title_-_overflow); text-overflow: var(--paper-font-title_-_text-overflow); font-size: var(--paper-font-title_-_font-size); font-weight: var(--paper-font-title_-_font-weight); line-height: var(--paper-font-title_-_line-height);
    }

    button.link {
      background: none;
        color: inherit;
        border: none;
        padding: 0;
        font: inherit;
        text-align: left;
        text-decoration: underline;
        cursor: pointer;
    }

    .card-actions a {
      text-decoration: none;
    }

    .card-actions .warning {
      --mdc-theme-primary: var(--google-red-500);
    }

    .card-group {
      margin-top: 24px;
    }

    .card-group .title {
      color: var(--primary-text-color);
        font-size: 1.5em;
        padding-left: 8px;
        margin-bottom: 8px;
    }

    .card-group .description {
      font-size: 0.5em;
        font-weight: 500;
        margin-top: 4px;
    }

    .card-group paper-card {
      --card-group-columns: 4;
        width: calc(
          (100% - 12px * var(--card-group-columns)) / var(--card-group-columns)
        );
        margin: 4px;
        vertical-align: top;
        height: 144px;
    }

    @media screen and (max-width: 1800px) and (min-width: 1201px) {
      .card-group paper-card {
        --card-group-columns: 3;
      }

      }

    @media screen and (max-width: 1200px) and (min-width: 601px) {
    .card-group paper-card {
      --card-group-columns: 2;
    }

    }

    @media screen and (max-width: 600px) and (min-width: 0) {
    .card-group paper-card {
      width: 100%;
          margin: 4px 0;
    }

    .content {
      padding: 0;
    }

    }

    ha-call-api-button {
      font-weight: 500;
        color: var(--primary-color);
    }

    .error {
      color: var(--google-red-500);
        margin-top: 16px;
    }

    paper-card {
      cursor: pointer;
    }
    ha-icon {
      margin-right: 16px;
      float: left;
      color: var(--primary-text-color);
    }
    ha-icon.update {
      color: var(--paper-orange-400);
    }
    ha-icon.running,
    ha-icon.installed {
      color: var(--paper-green-400);
    }
    ha-icon.hassupdate,
    ha-icon.snapshot {
      color: var(--paper-item-icon-color);
    }
    ha-icon.not_available {
      color: var(--google-red-500);
    }
    .title {
      margin-bottom: 16px;
      padding-top: 4px;
      color: var(--primary-text-color);
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .addition {
      color: var(--secondary-text-color);
      position: relative;
      height: 2.4em;
      line-height: 1.2em;
    }
    ha-relative-time {
      display: block;
    }
    `;
  }
}