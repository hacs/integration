export default {
  "plugins": [],
  "themes": [],
  "customFields": {},
  "themeConfig": {
    "navbar": {
      "title": "My Site",
      "logo": {
        "alt": "My Site Logo",
        "src": "img/logo.svg"
      },
      "links": [
        {
          "to": "docs/developer/start",
          "label": "Developer docs",
          "position": "right"
        },
        {
          "to": "help",
          "label": "Help",
          "position": "right"
        },
        {
          "href": "https://github.com/custom-components/hacs",
          "label": "GitHub",
          "position": "right"
        }
      ]
    },
    "footer": {
      "style": "dark",
      "links": [
        {
          "title": "Getting started",
          "items": [
            {
              "label": "Installation",
              "to": "docs/installation/manual"
            },
            {
              "label": "Configuration",
              "to": "docs/configuration/ui"
            },
            {
              "label": "Usage",
              "to": "docs/basic/getting_started"
            }
          ]
        },
        {
          "title": "More Links",
          "items": [
            {
              "label": "Community Forum",
              "href": "https://community.home-assistant.io/t/custom-component-hacs/121727"
            }
          ]
        }
      ]
    }
  },
  "title": "My Site",
  "tagline": "Home Assistant Community Store",
  "url": "https://your-docusaurus-test-site.com",
  "baseUrl": "/",
  "favicon": "",
  "organizationName": "custom-components",
  "projectName": "hacs",
  "presets": [
    [
      "@docusaurus/preset-classic",
      {
        "docs": {
          "editUrl": "https://github.com/custom-components/hacs/edit/master/documentation/docs/",
          "path": "./docs",
          "sidebarPath": "/workspaces/hacs/website/sidebars.js"
        },
        "theme": {
          "customCss": "/workspaces/hacs/website/src/css/custom.css"
        }
      }
    ]
  ]
};