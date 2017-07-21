import { combineReducers } from 'redux';

import {
	RECEIVE_IMPORT,
	REQUEST_IMPORT,
} from './actions';

import { dataToNewContacts } from './utils';


const defaultUI = {
	loading: false
};

function ui(state=defaultUI, action) {
	switch (action.type) {
		case RECEIVE_IMPORT:
			return Object.assign({}, state, {
				loading: false
			});

		case REQUEST_IMPORT:
			return Object.assign({}, state, {
				loading: true
			});

		default:
			return state;
	}
}

function importData(state={}, action) {
	switch (action.type) {
		case RECEIVE_IMPORT:
			return action.json;

		default:
			return state;
	}
}

function newContacts(state=[], action) {
	switch (action.type) {
		case RECEIVE_IMPORT:
			return dataToNewContacts(action.json);

		default:
			return state;
	}
}

const reviewEngine = combineReducers({
	importData,
	newContacts,
	ui
});

export default reviewEngine;
