import { combineReducers } from 'redux';

import {
	EDIT_FIELD,
	RECEIVE_IMPORT,
	REQUEST_IMPORT,
	START_EDIT_FIELD,
	STOP_EDIT_FIELD,
} from './actions';

import { dataToNewContacts, updateContact } from './utils';


const defaultUI = {
	loading: false,
	fieldEdit: null
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

		case START_EDIT_FIELD:
			return Object.assign({}, state, {
				fieldEdit: {
					row: action.row,
					field: action.field
				}
			});

		case STOP_EDIT_FIELD:
			return Object.assign({}, state, {
				fieldEdit: null
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
		case EDIT_FIELD:
			return updateContact(action, state);

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
