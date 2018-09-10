// Actions types

export const EDIT_FIELD = 'EDIT_FIELD';
export const RECEIVE_IMPORT = 'RECEIVE_IMPORT';
export const REQUEST_IMPORT = 'REQUEST_IMPORT';
export const START_EDIT_FIELD = 'START_EDIT_FIELD';
export const STOP_EDIT_FIELD = 'STOP_EDIT_FIELD';


export function editField(row, field, data) {
	return {
		type: EDIT_FIELD,
		row,
		field,
		data
	};
}

function receiveImport(json) {
	return {
		type: RECEIVE_IMPORT,
		json
	};
}

function requestImport() {
	return {
		type: REQUEST_IMPORT
	};
}

export function startEditField(row, field) {
	return {
		type: START_EDIT_FIELD,
		row,
		field
	};
}

export function stopEditField() {
	return {
		type: STOP_EDIT_FIELD
	};
}


// Async actions

export function fetchImport(pk) {
	return dispatch => {
		dispatch(requestImport());

		return fetch('/public/contacts/api/imports/' + pk + '/').then(
			response => response.json()
		).then(
			json => dispatch(receiveImport(json))
		);
	};
}
