/**
* A localisation widget that will display 3 circles that can be resized and will
* provide the radius in km.
*
* @param {google.maps.Map} map The map on which to attach the localisation widget.
* @param {data of widget} data The widget param to attach the localisation widget.
*
* @constructor
*/
    function LocalWidget(map, data, callChanged) {
        // Format data to number
        data.latitude = parseFloat(data.latitude);
        data.longitude = parseFloat(data.longitude);
        data.approachradius = parseFloat(data.approachradius);
        data.nearbyradius = parseFloat(data.nearbyradius);
        data.criticalradius = parseFloat(data.criticalradius);
        let latLng = new google.maps.LatLng({lat: data.latitude, lng: data.longitude});
        this.set('map', map);
        this.set('position', latLng);
        this.callChanged = callChanged
        this.device_id = data.id

        // Create new radius widget
        this.approachCircle = this.addRadiusWidget('Approach', {
                  strokeColor: '#0000FF',
                  strokeOpacity: 0.5,
                  strokeWeight: 1,
                  fillColor: '#0000FF',
                  fillOpacity: 0.15,
                  map: map,
                  center: {lat: data.latitude, lng: data.longitude},
                  radius: data.approachradius
                });

        this.nearbyCircle = this.addRadiusWidget('Nearby', {
                  strokeColor: '#FF8000',
                  strokeOpacity: 0.5,
                  strokeWeight: 1,
                  fillColor: '#FF8000',
                  fillOpacity: 0.15,
                  map: map,
                  center: {lat: data.latitude, lng: data.longitude},
                  radius: data.nearbyradius
                });

        this.criticalCircle = this.addRadiusWidget('Critical', {
                  strokeColor: '#DF0101',
                  strokeOpacity: 0.5,
                  strokeWeight: 1,
                  fillColor: '#DF0101',
                  fillOpacity: 0.15,
                  map: map,
                  center: {lat: data.latitude, lng: data.longitude},
                  radius: data.criticalradius
                });

        //****** Add markers
        var infowindow = new google.maps.InfoWindow();

        var marker = new google.maps.Marker({
          position: {lat: data.latitude, lng: data.longitude},
          map: map,
          title: data.name,
          draggable:true
        });

        var self = this
        marker.addListener('click', function() {
            infowindow.setContent('<div id="content">'+
                '<div id="siteNotice">'+
                '</div>'+
                '<h1 id="firstHeading" class="firstHeading">'+data.name+'</h1>'+
                '<div id="bodyContent">'+
                '<ul>'+
                '<li>Latitude : '+self.position.lat()+' </li>'+
                '<li>Longitude : '+self.position.lng()+' </li>'+
                '<li>Critcal radius : '+self.criticalCircle.distance+' km </li>'+
                '<li>Nearby radius : '+self.nearbyCircle.distance+' km </li>'+
                '<li>Approach radius : '+self.approachCircle.distance+' km </li>'+
                '</ul>'+
                '</div>'+
                '</div>');
            infowindow.open(map, marker);
        });

        // Bind the marker map property to the LocalWidget map property
        marker.bindTo('map', this);

        // Bind the marker position property to the LocalWidget position
        // property
        marker.bindTo('position', this);
        marker.bindTo('updated', this);
        google.maps.event.addListener(this.approachCircle, 'distance_changed', function () {
          updateParams(self, this);
        });
        google.maps.event.addListener(this.nearbyCircle, 'distance_changed', function () {
          updateParams(self, this);
        });
        google.maps.event.addListener(this.criticalCircle, 'distance_changed', function () {
          updateParams(self, this);
        });
        google.maps.event.addListener(this, 'position_changed', function () {
          updateParams(this);
        });

    }
    LocalWidget.prototype = new google.maps.MVCObject();

    LocalWidget.prototype.addRadiusWidget = function (name, data) {
        // Create new radius widget
        rWidget = new RadiusWidget(name, data);

        // Bind the radiusWidget map to the LocalWidget map
        rWidget.bindTo('map', this);

        // Bind the radiusWidget center to the LocalWidget position
        rWidget.bindTo('center', this, 'position');

        // Bind to the radiusWidgets' distance property
        this.bindTo('distance', rWidget);

        // Bind to the radiusWidgets' bounds property
        this.bindTo('bounds', rWidget);
        return rWidget
    }
    /**
    * A radius widget that add a circle to a map and centers on a marker.
    *
    * @constructor
    */
    function RadiusWidget(name, data) {
        var circle = new google.maps.Circle({
          strokeColor: data.strokeColor,
          strokeWeight: data.strokeWeight,
          strokeOpacity : data.strokeOpacity,
          fillColor: data.fillColor,
          fillOpacity: data.fillOpacity,
          map: data.map,
          center: data.center,
          radius: data.radius
        });
        this.name = name
        // Set the distance property value, default to 50km.
        this.set('distance', data.radius);

        // Bind the RadiusWidget bounds property to the circle bounds property.
        this.bindTo('bounds', circle);

        // Bind the circle center to the RadiusWidget center property
        circle.bindTo('center', this);

        // Bind the circle map to the RadiusWidget map
        circle.bindTo('map', this);

        // Bind the circle radius property to the RadiusWidget radius property
        circle.bindTo('radius', this);

        this.addSizer_();
    }
    RadiusWidget.prototype = new google.maps.MVCObject();

    /**
    * Update the radius when the distance has changed.
    */
    RadiusWidget.prototype.distance_changed = function () {
        this.set('radius', this.get('distance') * 1000);
    };
    /**
    * Add the sizer marker to the map.
    *
    * @private
    */
    RadiusWidget.prototype.addSizer_ = function () {
        var sizer = new google.maps.Marker({
            draggable: true,
            icon: {
              url: "https://maps.gstatic.com/intl/en_us/mapfiles/markers2/measle_blue.png",
              size: new google.maps.Size(7, 7),
              anchor: new google.maps.Point(4, 4)
            },
            title: 'Drag me!'
        });

        sizer.bindTo('map', this);
        sizer.bindTo('position', this, 'sizer_position');

        var me = this;
        google.maps.event.addListener(sizer, 'drag', function () {
          // Set the circle distance (radius)
            me.setDistance();
        });
    };

    /**
    * Update the center of the circle and position the sizer back on the line.
    *
    * Position is bound to the LocalWidget so this is expected to change when
    * the position of the distance widget is changed.
    */
    RadiusWidget.prototype.center_changed = function () {
      var bounds = this.get('bounds');

      // Bounds might not always be set so check that it exists first.
      if (bounds) {
          var lng = bounds.getNorthEast().lng();

          // Put the sizer at center, right on the circle.
          var position = new google.maps.LatLng(this.get('center').lat(), lng);
          this.set('sizer_position', position);
      }
    };

    /**
    * Calculates the distance between two latlng locations in km.
    * @see http://www.movable-type.co.uk/scripts/latlong.html
    *
    * @param {google.maps.LatLng} p1 The first lat lng point.
    * @param {google.maps.LatLng} p2 The second lat lng point.
    * @return {number} The distance between the two points in km.
    * @private
    */
    RadiusWidget.prototype.distanceBetweenPoints_ = function (p1, p2) {
      if (!p1 || !p2) {
          return 0;
      }

      var R = 6371; // Radius of the Earth in km
      var dLat = (p2.lat() - p1.lat()) * Math.PI / 180;
      var dLon = (p2.lng() - p1.lng()) * Math.PI / 180;
      var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(p1.lat() * Math.PI / 180) * Math.cos(p2.lat() * Math.PI / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
      var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      var d = R * c;
      return d;
    };

    /**
    * Set the distance of the circle based on the position of the sizer.
    */
    RadiusWidget.prototype.setDistance = function () {
      // As the sizer is being dragged, its position changes.  Because the
      // RadiusWidget's sizer_position is bound to the sizer's position, it will
      // change as well.
      var pos = this.get('sizer_position');
      var center = this.get('center');
      var distance = this.distanceBetweenPoints_(center, pos);

      // Set the distance property for any objects that are bound to it
      this.set('distance', distance);
    };

    function updateParams(widget, circle) {
        var info = document.getElementById('info');
        let dist = ', distances: ' + widget.criticalCircle.distance.toFixed(3) + ' / ' +
                    + widget.nearbyCircle.distance.toFixed(3) +' / ' + widget.approachCircle.distance.toFixed(3) +' km';
        if (circle != undefined) {
          dist = ', '+circle.name+' distance: ' + circle.distance.toFixed(3) +' km';
        }
        info.innerHTML = 'Position: ' + widget.get('position').toUrlValue(3) + dist;
        if (widget.callChanged != undefined) {widget.callChanged(widget);}
    }
