export default {
  "plugins": [],
  "themes": [],
  "customFields": {},
  "themeConfig": {
    "navbar": {
      "title": "HACS (Home Assistant Community Store)",
      "links": [
        {
          "to": "docs/installation/prerequisittes",
          "label": "Installation",
          "position": "left"
        },
        {
          "to": "docs/configuration/start",
          "label": "Configuration",
          "position": "left"
        },
        {
          "to": "docs/basic/getting_started",
          "label": "Usage",
          "position": "left"
        },
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
    }
  },
  "title": "HACS",
  "tagline": "Home Assistant Community Store",
  "url": "https://hacs.netlify.com",
  "baseUrl": "/",
  "favicon": "img/favicon.ico",
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