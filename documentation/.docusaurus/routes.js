
import React from 'react';
import ComponentCreator from '@docusaurus/ComponentCreator';

export default [
  
{
  path: '/help',
  component: ComponentCreator('/help'),
  exact: true,
  
},
{
  path: '/',
  component: ComponentCreator('/'),
  exact: true,
  
},
{
  path: '/docs',
  component: ComponentCreator('/docs'),
  
  routes: [
{
  path: '/docs/index',
  component: ComponentCreator('/docs/index'),
  exact: true,
  
},
{
  path: '/docs/basic/existing_elements',
  component: ComponentCreator('/docs/basic/existing_elements'),
  exact: true,
  
},
{
  path: '/docs/basic/data',
  component: ComponentCreator('/docs/basic/data'),
  exact: true,
  
},
{
  path: '/docs/issues',
  component: ComponentCreator('/docs/issues'),
  exact: true,
  
},
{
  path: '/docs/basic/getting_started',
  component: ComponentCreator('/docs/basic/getting_started'),
  exact: true,
  
},
{
  path: '/docs/basic/logs',
  component: ComponentCreator('/docs/basic/logs'),
  exact: true,
  
},
{
  path: '/docs/basic/sensor',
  component: ComponentCreator('/docs/basic/sensor'),
  exact: true,
  
},
{
  path: '/docs/basic/startup',
  component: ComponentCreator('/docs/basic/startup'),
  exact: true,
  
},
{
  path: '/docs/basic/updates',
  component: ComponentCreator('/docs/basic/updates'),
  exact: true,
  
},
{
  path: '/docs/categories/plugins',
  component: ComponentCreator('/docs/categories/plugins'),
  exact: true,
  
},
{
  path: '/docs/categories/integrations',
  component: ComponentCreator('/docs/categories/integrations'),
  exact: true,
  
},
{
  path: '/docs/categories/appdaemon_apps',
  component: ComponentCreator('/docs/categories/appdaemon_apps'),
  exact: true,
  
},
{
  path: '/docs/configuration/basic',
  component: ComponentCreator('/docs/configuration/basic'),
  exact: true,
  
},
{
  path: '/docs/configuration/legacy',
  component: ComponentCreator('/docs/configuration/legacy'),
  exact: true,
  
},
{
  path: '/docs/categories/python_scripts',
  component: ComponentCreator('/docs/categories/python_scripts'),
  exact: true,
  
},
{
  path: '/docs/categories/themes',
  component: ComponentCreator('/docs/categories/themes'),
  exact: true,
  
},
{
  path: '/docs/configuration/options',
  component: ComponentCreator('/docs/configuration/options'),
  exact: true,
  
},
{
  path: '/docs/developer/backend',
  component: ComponentCreator('/docs/developer/backend'),
  exact: true,
  
},
{
  path: '/docs/configuration/pat',
  component: ComponentCreator('/docs/configuration/pat'),
  exact: true,
  
},
{
  path: '/docs/configuration/start',
  component: ComponentCreator('/docs/configuration/start'),
  exact: true,
  
},
{
  path: '/docs/developer/devcontainer',
  component: ComponentCreator('/docs/developer/devcontainer'),
  exact: true,
  
},
{
  path: '/docs/developer/frontend',
  component: ComponentCreator('/docs/developer/frontend'),
  exact: true,
  
},
{
  path: '/docs/developer/documentation',
  component: ComponentCreator('/docs/developer/documentation'),
  exact: true,
  
},
{
  path: '/docs/developer/translation',
  component: ComponentCreator('/docs/developer/translation'),
  exact: true,
  
},
{
  path: '/docs/developer/start',
  component: ComponentCreator('/docs/developer/start'),
  exact: true,
  
},
{
  path: '/docs/installation/prerequisittes',
  component: ComponentCreator('/docs/installation/prerequisittes'),
  exact: true,
  
},
{
  path: '/docs/publish/appdaemon',
  component: ComponentCreator('/docs/publish/appdaemon'),
  exact: true,
  
},
{
  path: '/docs/installation/manual',
  component: ComponentCreator('/docs/installation/manual'),
  exact: true,
  
},
{
  path: '/docs/publish/blacklist',
  component: ComponentCreator('/docs/publish/blacklist'),
  exact: true,
  
},
{
  path: '/docs/publish/integration',
  component: ComponentCreator('/docs/publish/integration'),
  exact: true,
  
},
{
  path: '/docs/publish/plugin',
  component: ComponentCreator('/docs/publish/plugin'),
  exact: true,
  
},
{
  path: '/docs/publish/include',
  component: ComponentCreator('/docs/publish/include'),
  exact: true,
  
},
{
  path: '/docs/publish/python_script',
  component: ComponentCreator('/docs/publish/python_script'),
  exact: true,
  
},
{
  path: '/docs/publish/theme',
  component: ComponentCreator('/docs/publish/theme'),
  exact: true,
  
},
{
  path: '/docs/publish/start',
  component: ComponentCreator('/docs/publish/start'),
  exact: true,
  
}],
},
  
  {
    path: '*',
    component: ComponentCreator('*')
  }
];
