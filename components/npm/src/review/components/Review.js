import React, { Component } from 'react';

import { connect } from 'react-redux';

import {
	fetchImport,
} from '../actions';

import { stopEditField } from '../actions';

import { Contact } from './Contact';


class Loading extends Component {
	render() {
		if (!this.props.ui.loading) {
			return false;
		}

		return <div>Loading...</div>;
	}
}

class Header extends Component {
	render() {
		return <thead>
			<tr>
				<th>Row</th>
				{this.props.fields.map((field, index) =>
					<th key={index}>{field[1]}</th>)}
			</tr>
		</thead>;
	}
}

class NewContacts extends Component {
	render() {
		if (this.props.newContacts.length === 0) {
			return false;
		}

		let newContacts = this.props.newContacts.map(
			(contact, index) => <Contact
				key={index}
				fields={contact}
				contactFields={this.props.contactFields}
				ui={this.props.ui}
				dispatch={this.props.dispatch}
				getCountry={this.props.getCountry}
				getRegion={this.props.getRegion}
				getCountries={this.props.getCountries}
				getRegions={this.props.getRegions}
				getGroups={this.props.getGroups}
			/>
		);

		return <div className="new-contacts">
			<h2>New contacts</h2>
			<table>
			<Header fields={this.props.contactFields} />
			<tbody>
				{newContacts}
			</tbody>
			</table>
		</div>;
	}
}

class Review extends Component {
	handleKeyDown(e) {
		// Stop edit on Enter or Escape
		if (this.props.ui.fieldEdit === null) {
			return;
		}

		if (['Enter', 'Escape'].includes(e.key)) {
			this.props.dispatch(stopEditField());
		}
	}

	componentWillMount() {
		document.addEventListener('keydown', this.handleKeyDown.bind(this), false);
	}

	componentWillUnmount() {
		document.removeEventListener('keydown', this.handleKeyDown.bind(this), false);
	}

	getCountry(pk) {
		return this.props.importData.countries.find(
			country => country.pk === parseInt(pk));
	}

	getRegion(pk) {
		return this.props.importData.regions.find(
			region => region.pk === pk);
	}

	getCountries() {
		return this.props.importData.countries;
	}

	getRegions(country) {
		return this.props.importData.regions.filter(region =>
			region.country === country
		);
	}

	getGroups() {
		return this.props.importData.groups.map(group => group.name);
	}

	componentDidMount() {
		this.props.dispatch(fetchImport(importPK));
	}

	render() {
		return <div>
			<h1>Import review</h1>
			<Loading ui={this.props.ui} />
			<NewContacts
				newContacts={this.props.newContacts}
				contactFields={this.props.importData.contact_fields}
				ui={this.props.ui}
				dispatch={this.props.dispatch}
				getCountry={this.getCountry.bind(this)}
				getRegion={this.getRegion.bind(this)}
				getCountries={this.getCountries.bind(this)}
				getRegions={this.getRegions.bind(this)}
				getGroups={this.getGroups.bind(this)}
			/>
		</div>;
	}
}


function select(state) {
	return {
		importData: state.importData,
		newContacts: state.newContacts,
		ui: state.ui
	};
}

export default connect(select)(Review);
