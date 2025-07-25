'use strict'

process.env.NODE_ENV = 'development'

const utils = require('./utils')
const webpack = require('webpack')
const config = require('../config')
const { merge } = require('webpack-merge')
const path = require('path')
const baseWebpackConfig = require('./webpack.base.conf')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')
const portfinder = require('portfinder')
const { VueLoaderPlugin }  = require('vue-loader')
const cesiumSource =  'node_modules/cesium/Source'
const cesiumWorkers = '../Build/Cesium/Workers'
const GitRevisionPlugin = require('git-revision-webpack-plugin')
const gitRevisionPlugin = new GitRevisionPlugin()
const ESLintPlugin = require('eslint-webpack-plugin');


const HOST = '0.0.0.0'
const PORT = process.env.PORT && Number(process.env.PORT)

const devWebpackConfig = merge(baseWebpackConfig, {
    mode: 'development',
  module: {
    rules: utils.styleLoaders({ sourceMap: config.dev.cssSourceMap, usePostCSS: true })
  },
  // cheap-module-eval-source-map is faster for development
  devtool: config.dev.devtool,

  stats: {
    children: true,
  },
  // these devServer options should be customized in /config/index.js
  devServer: {
    client: {
      overlay: config.dev.errorOverlay
        ? { warnings: false, errors: true }
        : false,
        logging: 'warn',

    },
    historyApiFallback: {
      rewrites: [
        { from: /.*/, to: path.posix.join(config.dev.assetsPublicPath, 'index.html') },
      ],
    },
    hot: false, // Disabled for better stability
    liveReload: false, // Disabled for better stability
    static: "./",
    compress: true,
    host: HOST || config.dev.host,
    port: PORT || config.dev.port,
    open: config.dev.autoOpenBrowser,
   // publicPath: config.dev.assetsPublicPath,
    proxy: config.dev.proxyTable,
    watchFiles: {
      paths: ['src/**/*'],
      options: {
        ignored: /node_modules/,
        usePolling: false,
      },
    },
  },
  plugins: [
    // new ESLintPlugin({fix: true}), // Disabled for better performance
    new webpack.DefinePlugin({
      'process.env': require('../config/dev.env'),
      '_COMMIT_': JSON.stringify(gitRevisionPlugin.commithash()),
      '_BUILDDATE_': JSON.stringify((new Date().toString()))
    }),
    // new webpack.HotModuleReplacementPlugin(), // Disabled for better stability
    new webpack.NoEmitOnErrorsPlugin(),
    // https://github.com/ampedandwired/html-webpack-plugin
    new HtmlWebpackPlugin({
      filename: 'index.html',
      template: 'index.html',
      inject: true
    }),
    // copy custom static assets
    new CopyWebpackPlugin({
      patterns: [
        { from: path.resolve(cesiumSource, cesiumWorkers), to: 'Workers' },
        { from: path.resolve(cesiumSource, 'Assets'), to: 'Assets' },
        { from: path.resolve(cesiumSource, 'Widgets'), to: 'Widgets' },
        { from: path.resolve(cesiumSource, 'ThirdParty/Workers'), to: 'ThirdParty/Workers' },
      ],
      options: {
        concurrency: 100
      }
    }),
    new webpack.DefinePlugin({
      // Define relative base path in cesium for loading assets
      CESIUM_BASE_URL: JSON.stringify('')
    }),
      new VueLoaderPlugin(),
  ]
})

module.exports = new Promise((resolve, reject) => {
  portfinder.basePort = process.env.PORT || config.dev.port
  portfinder.getPort((err, port) => {
    if (err) {
      reject(err)
    } else {
      // publish the new Port, necessary for e2e tests
      process.env.PORT = port
      // add port to devServer config
      devWebpackConfig.devServer.port = port
      resolve(devWebpackConfig)
    }
  })
})
