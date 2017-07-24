import React, { Component } from 'react';

import { editField, startEditField } from '../actions';

class RegionField extends Component {
	handleChange(e) {
		this.props.dispatch(
			editField(this.props.fields.row, this.props.field, e.target.value)
		);
	}

	render() {
		let value = this.props.value;
		if (value === null) {
			value = '';
		}

		if (this.props.edit === false) {
			if (value === '') {
				return false;
			}

			let region = this.props.getRegion(value);
			return <span>{region.name}</span>;
		} else {
			// Region only make sense if we have a country selected
			if (this.props.fields.country === null) {
				return false;
			}

			let regions = this.props.getRegions(this.props.fields.country);
			if (regions.length === 0) {
				return false;
			}

			return <select
				value={value}
				onChange={this.handleChange.bind(this)}
			>
				{regions.map( (region, index) =>
					<option
						key={index}
						value={region.pk}
					>
						{region.name}
					</option>
				)}
			</select>;
		}
	}
}

class CountryField extends Component {
	handleChange(e) {
		this.props.dispatch(
			editField(this.props.fields.row, this.props.field, e.target.value)
		);
	}

	render() {
		if (this.props.edit === false) {
			let country = this.props.getCountry(this.props.value);
			return <span>{country.name}</span>;
		} else {
			return <select
				value={this.props.value}
				onChange={this.handleChange.bind(this)}
			>
				{this.props.getCountries().map((country, index) =>
					<option
						key={index}
						value={country.pk}
					>
						{country.name}
					</option>
				)}
			</select>;
		}
	}
}

class GroupsField extends Component {
	handleChange(e) {
		console.log(e.target.options);
		let options = e.target.options;
		let values = [];

		values = [...e.target.options].filter(option => option.selected).map(
			option => option.value
		);

		this.props.dispatch(
			editField(this.props.fields.row, this.props.field, values)
		);
	}

	render() {
		let value = this.props.value;
		if (value === null) {
			value = '';
		}

		if (this.props.edit === false) {
			return <span>{value}</span>;
		} else {
			return <select
				value={this.props.groups}
				onChange={this.handleChange.bind(this)}
				multiple="multiple"
			>
				{this.props.getGroups().map((group, index) =>
					<option
						key={index}
						value={group}
					>
						{group}
					</option>
				)}
			</select>;
		}
	}
}

class TextField extends Component {
	handleChange(e) {
		this.props.dispatch(
			editField(this.props.fields.row, this.props.field, e.target.value)
		);
	}

	render() {
		let value = this.props.value;
		if (value === null) {
			value = '';
		}

		if (this.props.edit === false) {
			return <span>{value}</span>;
		} else {
			return <input
				autoFocus
				value={value}
				onChange={this.handleChange.bind(this)}
			/>;
		}
	}
}

class Field extends Component {
	render() {
		let field = false;
		let edit = false;

		if (this.props.ui.fieldEdit !== null &&
			this.props.ui.fieldEdit.row === this.props.fields.row &&
			this.props.ui.fieldEdit.field === this.props.field) {
			edit = true;
		}

		switch (this.props.field) {
			case 'country':
				field = <CountryField {...this.props} edit={edit} />;
				break;

			case 'region':
				field = <RegionField {...this.props} edit={edit} />;
				break;

			case 'groups':
				field = <GroupsField {...this.props} edit={edit} />;
				break;

			default:
				field = <TextField {...this.props} edit={edit} />;
				break;
		}

		let onClick = null;
		if (this.props.field !== 'row' && edit === false) {
			onClick = () => this.props.dispatch(
				startEditField(this.props.fields.row, this.props.field)
			);
		}

		return <td
			onClick={onClick}
		>
			{field}
		</td>;
	}
}

export class Contact extends Component {
	shouldComponentUpdate(nextProps, nextState) {
		if (nextProps.ui.fieldEdit !== null &&
			nextProps.ui.fieldEdit.row === this.props.fields.row) {
			// Contact is being edited
			return true;
		}

		if (this.props.ui.fieldEdit !== null &&
			this.props.ui.fieldEdit.row === this.props.fields.row) {
			// Contact was being edited
			return true;
		}

		return false;
	}

	getField(key, field, name) {
		return <Field
			key={key}
			field={field}
			name={name}
			value={this.props.fields[field]}
			{...this.props}
		/>;
	}

	render() {
		let fields = this.props.contactFields.map((field, index) =>
			this.getField(index + 1, field[0], field[1]));

		return <tr>
			{this.getField(0, 'row', 'Row')}
			{fields}
		</tr>;
	}
}
