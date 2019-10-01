import {
  LitElement,
  customElement,
  CSSResultArray,
  TemplateResult,
  html,
  css,
  property
} from "lit-element";

import { HomeAssistant } from "custom-card-helpers";

import { HacsStyle } from "../style/hacs-style"
import { Configuration, Repository } from "../types"
import { navigate } from "../misc/navigate"

@customElement("hacs-panel")
export class HacsPanelStore extends LitElement {

  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repository[]

  @property()
  public configuration!: Configuration

  @property()
  public panel;

  @property()
  public repository_view = false;

  @property()
  public repository: string;

  @property()
  public SearchTerm: string = "";

  protected render(): TemplateResult | void {
    if (this.panel === "repository") {
      // How fun, this is a repository!
      return html`
      <hacs-panel-repository
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repositories=${this.repositories}
        .repository=${this.repository}
      >
      </hacs-panel-repository>`
    } else {

      const category = this.panel;
      const config = this.configuration;
      this.SearchTerm = localStorage.getItem("hacs-search");
      var SearchTerm = this.SearchTerm;
      var _repositories = this.repositories.filter(function (repo) {

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

        if (repo.category === category) {
          if (SearchTerm !== "" || null) {
            if (repo.name.toLowerCase().includes(SearchTerm)) return true;
            if (repo.description.toLowerCase().includes(SearchTerm)) return true;
            if (repo.full_name.toLowerCase().includes(SearchTerm)) return true;
            if (String(repo.authors).toLowerCase().includes(SearchTerm)) return true;
            if (String(repo.topics).toLowerCase().includes(SearchTerm)) return true;
            return false;
          }

          // Fallback to not showing it if no search.
          return true;
        }
        // Fallback to not showing it.
        return false
      });

      return html`
      <paper-input
        class="search-bar search-bar-${this.panel}"
        type="text"
        id="Search"
        @input=${this.DoSearch}
        placeholder="  ${this.hass.localize("component.hacs.store.placeholder_search")}."
        autofocus
        .value=${this.SearchTerm}
      ></paper-input>

    <div class="card-group">
    ${_repositories.sort((a, b) => (a.name > b.name) ? 1 : -1).map(repo =>
        html`

      <paper-card id="${repo.id}" @click="${this.ShowRepository}" .RepoID="${repo.id}">
      <div class="card-content">
        <div>
          <ha-icon
            icon="mdi:cube"
            class="${repo.status}"
            title="${repo.status_description}"
            >
          </ha-icon>
          <div>
            <div class="title">${repo.name}</div>
            <div class="addition">${repo.description}</div>
          </div>
        </div>
      </div>
      </paper-card>
      `)}
    </div>
    <script>
    var objDiv = document.getElementById("191563578");
    objDiv.scrollTop = objDiv.scrollHeight;
    console.log("done")
    </script>
          `;
    }
  }

  DoSearch(ev) {
    this.SearchTerm = ev.path[0].value.toLowerCase();
    localStorage.setItem("hacs-search", this.SearchTerm);
  };

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

  static get styles(): CSSResultArray {
    return [
      HacsStyle,
      css`
        .search-bar {
          display: block;
          width: 92%;
          margin-left: 3.4%;
          margin-top: 2%;
          background-color: var(--primary-background-color);
          color: var(--primary-text-color);
          line-height: 32px;
          border-color: var(--dark-primary-color);
          border-width: inherit;
          border-bottom-width: thin;
      }

      .search-bar-installed, .search-bar-settings {
        display: none;
      }

      .card-group {
          margin-top: 24px;
          width: 95%;
          margin-left: 2.5%;
        }

        .card-group .title {
          color: var(--primary-text-color);
          margin-bottom: 12px;
        }

        .card-group .description {
          font-size: 0.5em;
          font-weight: 500;
          margin-top: 4px;
        }

        .card-group paper-card {
          --card-group-columns: 3;
          width: calc((100% - 12px * var(--card-group-columns)) / var(--card-group-columns));
          margin: 4px;
          vertical-align: top;
          height: 136px;
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
    `];
  }
}