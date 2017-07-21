import 'babel-polyfill';
import { createLogger } from 'redux-logger';
import { createStore, applyMiddleware } from 'redux';
import { Provider } from 'react-redux';
import React from 'react';
import { render } from 'react-dom';
import thunkMiddleware from 'redux-thunk';

import Review from './review/components/Review';
import reviewEngine from './review/reducers';

let rootElement = document.getElementById('review');
const loggerMiddleware = createLogger();
const createStoreWithMiddleware = applyMiddleware(
	thunkMiddleware,
	loggerMiddleware
)(createStore);

const store = createStoreWithMiddleware(reviewEngine);


render(
	<Provider store={store}>
		<Review />
	</Provider>,
	rootElement
);
