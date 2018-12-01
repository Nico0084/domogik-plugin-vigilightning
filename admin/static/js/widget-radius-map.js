/**
* A localisation widget that will display 3 circles that can be resized and will
* provide the radius in km.
*
* @param {L.map} map The map on which to attach the localisation widget.
* @param {data of widget} data The widget param to attach the localisation widget.
*/

var IconOffset = [12, 32];

function propertyBindTo(key, source) {
    return source[key]
}

function getTimeImage(time, reftime) {
    const  prefix = (reftime == undefined) ? 'cur-strike-t' : 'his-strike-t'
    let current = (reftime == undefined) ? Math.floor(Date.now() / 1000) : reftime;
    let delta =  current - time;
    let num = '6';
    if (delta <= 120) {     // 2 mins
        num = '1';}
    else if (delta <= 240) {     // 4 mins
        num = '2';}
    else if (delta <= 400) {     // 7 mins
        num = '3';}
    else if (delta <= 600) {     // 10 mins
        num = '4';}
    else if (delta <= 900) {    // 15 mins
        num = '5';}
    return '/plugin_vigilightning/static/images/'+ prefix + num +'.png';
}


/**
*/
    var LocalWidget = L.Marker.extend({
        options: {
            // @option callChanged: function  = null
            // Function to call when widget is changed
            callChanged : null,
        },

        initialize: function (latlng, options, map, data) {
            L.Marker.prototype.initialize.call(this, latlng, options);
            // Format data to number
            data.latitude = parseFloat(data.latitude);
            data.longitude = parseFloat(data.longitude);
            data.approachradius = parseFloat(data.approachradius);
            data.nearbyradius = parseFloat(data.nearbyradius);
            data.criticalradius = parseFloat(data.criticalradius);
            let latLng = L.latLng({lat: data.latitude, lng: data.longitude});
            this.map = map;
            this._latlng = latLng;
            this.device_id = data.id;
            this.strikes = {};
            this.timerStrikes = {};
            var self = this;
            this.alertLevel = 0;
            this.blinking = null;

            // Create new radius widget
            this.approachCircle = new RadiusWidget([this._latlng.lat, this._latlng.lng], {
                      name: 'Approach',
                      strokeColor: '#0000FF',
                      strokeOpacity: 0.5,
                      strokeWeight: 1,
                      fillColor: '#0000FF',
                      fillOpacity: 0.15,
                      center: {lat: data.latitude, lng: data.longitude},
                      radius: data.approachradius * 1000.00,
                      editable: true,
                      draggable:false
                    });

            this.nearbyCircle = new RadiusWidget([this._latlng.lat, this._latlng.lng], {
                      name: 'Nearby',
                      strokeColor: '#FF8000',
                      strokeOpacity: 0.5,
                      strokeWeight: 1,
                      fillColor: '#FF8000',
                      fillOpacity: 0.15,
                      map: this.map,
                      center: {lat: data.latitude, lng: data.longitude},
                      radius: data.nearbyradius * 1000.00,
                      editable: true,
                      draggable:false
                    });

            this.criticalCircle =  new RadiusWidget([this._latlng.lat, this._latlng.lng], {
                      name: 'Critical',
                      strokeColor: '#DF0101',
                      strokeOpacity: 0.5,
                      strokeWeight: 1,
                      fillColor: '#DF0101',
                      fillOpacity: 0.15,
                      map: this.map,
                      center: {lat: data.latitude, lng: data.longitude},
                      radius: data.criticalradius * 1000.00,
                      editable: true,
                      draggable:false
                    });

            setInterval(self.refreshStrikes.bind(this), 10000);

            this.bindPopup(function(){return '<div id="content">'+
                    '<div id="siteNotice">'+
                    '</div>'+
                    '<h1 id="firstHeading" class="firstHeading">'+data.name+'</h1>'+
                    '<div id="bodyContent">'+
                    '<ul>'+
                    '<li>Latitude : '+this.getLatLng().lat+' </li>'+
                    '<li>Longitude : '+this.getLatLng().lng+' </li>'+
                    '<li>Critical radius : '+self.criticalCircle.getRadius()/1000+' km </li>'+
                    '<li>Nearby radius : '+self.nearbyCircle.getRadius()/1000+' km </li>'+
                    '<li>Approach radius : '+self.approachCircle.getRadius()/1000+' km </li>'+
                    '</ul>'+
                    '</div>'+
                    '</div>'
            });
            this.on('move', function (event) {
                if (!latlngEqual(self.approachCircle._latlng, this._latlng)) self.approachCircle.updatePos([this._latlng.lat, this._latlng.lng]);
                if (!latlngEqual(self.nearbyCircle._latlng, this._latlng)) self.nearbyCircle.updatePos([this._latlng.lat, this._latlng.lng]);
                if (!latlngEqual(self.criticalCircle._latlng, this._latlng)) self.criticalCircle.updatePos([this._latlng.lat, this._latlng.lng]);
                updateParams(self);
            });

            this.approachCircle.on('editable:vertex:drag', function (event) {
                updateParams(self, this);
            });
            this.nearbyCircle.on('editable:vertex:drag', function (event) {
                updateParams(self, this);
            });
            this.criticalCircle.on('editable:vertex:drag', function (event) {
                updateParams(self, this);
            });
            // Show the lat and lng under the mouse cursor.
            var coordsDiv = document.getElementById('coords_'+this.device_id);
            map.on('mousemove', function(event) {
                coordsDiv.textContent =
                    'lat: ' + event.latlng.lat.toFixed(6)+ ', ' +
                    'lng: ' + event.latlng.lng.toFixed(6);
                });
        },
        updateChilds(event, source) {
                    if (!latlngEqual(this.approachCircle._latlng, event.latlng)) this.approachCircle.updatePos([event.latlng.lat, event.latlng.lng]);
                    if (!latlngEqual(this.nearbyCircle._latlng, event.latlng)) this.nearbyCircle.updatePos([event.latlng.lat, event.latlng.lng]);
                    if (!latlngEqual(this.criticalCircle._latlng , event.latlng)) this.criticalCircle.updatePos([event.latlng.lat, event.latlng.lng]);
                    if (!latlngEqual(this._latlng, event.latlng)) this.setLatLng([event.latlng.lat, event.latlng.lng]);
        },
        addTo: function(map) {
            // call parent function
            L.Marker.prototype.addTo.call(this, map);
            // add all childrens objects
            this.approachCircle.addTo(map);
            this.nearbyCircle.addTo(map);
            this.criticalCircle.addTo(map);
            this.setEditable(true);
        },
        setEditable: function(enable) {
            this.editable = enable;
            if (this.editable && this._map) {
                this.approachCircle.enableEdit();
                this.nearbyCircle.enableEdit();
                this.criticalCircle.enableEdit();
            } else if (this._map) {
                this.approachCircle.disableEdit();
                this.nearbyCircle.disableEdit();
                this.criticalCircle.disableEdit();
            }
        },
        getBounds: function () {
            return this.approachCircle.getBounds();
        },
        addStrike: function (strike) {
            let strikeID = strike.latitude+","+strike.longitude;
            this.strikes[strikeID] = (L.marker([strike.latitude, strike.longitude], {
                                                      icon: new StrikeIcon({iconUrl: getTimeImage(strike.time)}),
                                                      time: strike.time}
                                                    ).bindPopup('<span>'+new Date(strike.time*1000).toLocaleString()+ "<br>" +
                                                        'Latitude: ' + strike.latitude.toFixed(6) + '<br>' +
                                                        'Longitude: ' + strike.longitude.toFixed(6) + '</span>')
                                                  );
            this.strikes[strikeID].addTo(this.map);
            this.timerStrikes[strikeID] = setInterval(function(strikeID, self) {
                if (self.strikes[strikeID].options.time + 30 >= (Date.now() / 1000)) {
                    self.strikes[strikeID].getElement().style.visibility = (self.strikes[strikeID].getElement().style.visibility == 'visible') ? 'hidden' : 'visible';
                } else {
                    self.strikes[strikeID].getElement().style.visibility = 'visible';
                    clearInterval(self.timerStrikes[strikeID]);
                }
            }, 300, strikeID, this);
        },
        deleteStrike: function (strike) {
            s = this.strikes.indexOf(strike);
            if (s >= 0) {
                this.strikes[s].remove()
                this.strikes.splice(s, 1);
            }
        },
        showStrikes: function () {
            for (s in this.strikes) {
                this.strikes[s].getElement().style.visibility = 'visible';
            }
        },
        hideStrikes: function () {
            for (s in this.strikes) {
                this.strikes[s].getElement().style.visibility = 'hidden';
            }
        },
        refreshStrikes: function () {
            for (s in this.strikes) {
                this.strikes[s].setIcon(new StrikeIcon({iconUrl: getTimeImage(this.strikes[s].options.time)}));
            }
        },
        handleAlert: function (alertLevel) {
            this.alertLevel = alertLevel;
            if (this.alertLevel == 0)  {
                if (this.blinking != null) {
                    clearInterval(this.blinking);
                    this.blinking = null;
                }
            } else {
                if (this.blinking == null) {
                    this.blinking = setInterval(this.blinkAlert.bind(this), 500);
                }
            }
        },
        blinkAlert: function () {
            switch (this.alertLevel) {
                case 3 :
                        this.criticalCircle.toggleVisible();
                        this.nearbyCircle.setVisible(true);
                        this.approachCircle.setVisible(true);
                    break;
                case 2 :
                        this.nearbyCircle.toggleVisible();
                        this.criticalCircle.setVisible(true);
                        this.approachCircle.setVisible(true);
                    break;
                case 1 :
                        this.approachCircle.toggleVisible();
                        this.nearbyCircle.setVisible(true);
                        this.criticalCircle.setVisible(true);
                    break;
            }
        }
    })
    /**
    * A radius widget that add a circle to a map and centers on a marker.
    *
    * Extend leaflet Circle Class
    */
    var RadiusWidget = L.Circle.extend({
        options: {
            // @option name: String  = ''
            // The name of type level
            name : '',
            editable: false
        },
        initialize: function (latlng, options, data) {
            L.Circle.prototype.initialize.call(this, latlng, options);
            this.skipMiddleMarkers = true;
        },
        toggleVisible: function () {
            let state = 'visible';
            if (this.getElement().style.visibility == state) state = 'hidden';
            this.getElement().style.visibility = state;
        },
        setVisible: function (state) {
            this.getElement().style.visibility =  state ? 'visible' : 'hidden';
        },
        getDistance: function () {
            return this.getRadius() / 1000;
        },
        /**
        * Update the center of the circle and position the sizer back on the line.
        *
        * Position is bound to the LocalWidget so this is expected to change when
        * the position of the distance widget is changed.
        */
        updatePos: function (latLng) {
            let editable = this.editEnabled;
            if (editable) this.disableEdit();
            this.setLatLng(latLng);
            if (editable) this.enableEdit();
        }
    });

// Hack leaflet.Editable plugin to hidden vertex center control to avoid circle drag
L.Editable.VertexMarker.prototype.onAdd = function (map) {
    L.Marker.prototype.onAdd.call(this, map);
    if (['Approach', 'Nearby', 'Critical'].indexOf(this.editor.feature.options.name) !== -1 && this.getIndex() === 0) {
        this.getElement().style.display = 'none';
    } else {
        this.on('drag', this.onDrag);
        this.on('dragstart', this.onDragStart);
        this.on('dragend', this.onDragEnd);
        this.on('mouseup', this.onMouseup);
        this.on('click', this.onClick);
        this.on('contextmenu', this.onContextMenu);
        this.on('mousedown touchstart', this.onMouseDown);
        this.on('mouseover', this.onMouseOver);
        this.on('mouseout', this.onMouseOut);
    }
    this.addMiddleMarkers();
}

var StrikeIcon = L.Icon.extend({
    options: {
        iconUrl : '',
        iconSize:     [32, 32], // size of the icon
        iconAnchor:   IconOffset, // point of the icon which will correspond to marker's location
        popupAnchor:  [0, -34], // point from which the popup should open relative to the iconAnchor
        time : 0
    }
});

function latlngEqual(p1, p2) {
    return (p1.lat == p2.lat && p1.lng == p2.lng);
}

function updateParams(widget, circle) {
    var info = document.getElementById('info_'+widget.device_id);
    let dist = ', distances: ' + parseFloat(widget.criticalCircle._mRadius/1000).toFixed(3) + ' / ' +
                parseFloat(widget.nearbyCircle._mRadius/1000).toFixed(3) +' / ' +
                parseFloat(widget.approachCircle._mRadius/1000).toFixed(3) +' km';
    if (circle != undefined) {
      dist = ', '+circle.options.name+' distance: ' + parseFloat(circle._mRadius/1000).toFixed(3) +' km';
    }
    info.innerHTML = 'Position: ' + widget._latlng + dist;
    if (widget.options.callChanged != undefined) {widget.options.callChanged(widget);}
}
