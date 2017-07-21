import React from 'react';
import { connect } from 'react-redux';

import { visibilityFilters } from '../actions';
import { searchString } from '../utils';

const { SHOW_ALL, SHOW_ONLINE, SHOW_OFFLINE } = visibilityFilters;


class Screenshot extends React.Component {
	render() {
		let src = this.props.src;
		let img = '';
		let frozen = '';

		if (src === null) {
			img = <img src="/static/screenshot/blank.png" />;
		} else {
			img = <img src={this.props.src} />;

			if (this.props.frozen) {
				frozen = <div className="frozen">Frozen</div>;
			}
		}

		return (
			<div className="screenshot">
				{img}
				{frozen}
			</div>
		);
	}
}


class Client extends React.Component {
	render() {
		let classes = 'client ';

		if (this.props.online && !this.props.frozen_screenshot) {
			classes += 'online';
		} else {
			classes += 'offline';
			if (!this.props.monitor) {
				classes += ' nomonitor';
			}
		}

		let lastSeen = this.props.last_seen === null ? 'Never' :
							moment(this.props.last_seen).fromNow();

		let active = '';
		if (this.props.active) {
			active = <span className="label label-success">Active</span>;
		} else {
			active = <span className="label label-danger">Inactive</span>;
		}

		let slug = '';
		let playlist = false;
		if (this.props.app === null) {
			slug = <span className="label label-warning">Not configured</span>;
		} else {
			slug = <span className="label label-default">{this.props.app.slug}</span>;
			playlist = <a
				style={{marginRight: '5px'}}
				href={'/v3/playlist/' + this.props.app.slug + '/'}
			><i className="fa fa-list"></i></a> ;
		}

		let adminURL = '/admin/v3/client/' + this.props.pk + '/';

		return (
			<div className="col-lg-3 col-md-4 col-sm-6">
				<div className={classes}>
					<Screenshot src={this.props.screenshot} frozen={this.props.frozen_screenshot} />
					<div className="caption">
						<strong>{this.props.hostname}:</strong> {this.props.name}<br />
						Last seen {lastSeen}<br />
						<div className="active">{slug} {active}</div>
						<div className="admin">
							{playlist}
							<a href={adminURL}><i className="fa fa-edit"></i></a>
						</div>
					</div>
				</div>
			</div>
		);
	}
}


export default class Clients extends React.Component {
	render() {
		let clientNodes = this.props.clients.filter(
			client => {
				switch (this.props.ui.visibilityFilter) {
					case SHOW_ALL:
						return true;
					case SHOW_ONLINE:
						return client.online;
					case SHOW_OFFLINE:
						return !client.online;
				}
			}
		).filter(
			client => {
				let s = this.props.ui.searchFilter;

				if (s === '') {
					return true;
				}

				let fields = [client.hostname, client.description, client.name];
				if (client.app !== null) {
					fields.push(client.app.slug);
				}

				return fields.some((field) => searchString(s, field));
			}
		).map(
			(client, index) => <Client {...client} key={index} />
		);

		if (clientNodes.length === 0) {
			return (
				<div className="message">No clients found</div>
			);
		}

		return (
			<div className="clients container-fluid">
				<div className="row">
					{clientNodes}
				</div>
			</div>
		);
	}
}
