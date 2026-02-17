#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import App from './App.js';

// 全屏渲染
render(<App />, { fullscreen: true });
