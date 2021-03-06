'use strict';

// Services
angular.module('ldmlEdit.service', [ 'ngResource' ])
  .service('DomService', ['$http', function($http) {
    var et = null;
    var nsResolver;

    var newET = function() {
        et = new ElementTree(null);
        et.root.attributes['xmlns:sil'] = 'urn://www.sil.org/ldml/0.1';
    };
    this.loadFromFile = function(file, cb) {
        var reader = new FileReader();
        reader.onload = function(e) {
            var dat = reader.result;
            var parser = new DOMParser();
            var dom = parser.parseFromString(dat,"text/xml");
            et = new ElementTree(dom);
            cb(et);
        };
        reader.readAsText(file);
    };
    this.loadFromURL = function(url, cb) {
        var ldml = $http.get(url).success(function(result) {
            var parser = new DOMParser();
            var dom = parser.parseFromString(result, "text/xml");
            et = new ElementTree(dom);
            cb(et);
        }).error(function(result) { cb(null); });
    };
    this.updateTopLevel = function(el) {
        for (var i = 0; i < et.root.children.length; i++)
            if (et.root.children[i].tag == el.tag)
                return;
        et.root.children.push(el);
    };
    this.findElement = function(base, tag) {
        if (base == null) {
            if (et == null)
                newET();
            base = et.root;
        }
        if (base.children == null)
            return null;
        for (var i = 0; i < base.children.length; i++) {
            if (base.children[i].tag == tag)
                return base.children[i];
        }
        return null;
    }
    this.findElements = function(base, tags) {
        var res = base;
        if (base == null) {
            if (et == null)
                newET();
            base = et.root;
        }
        for (var i = 0; i < tags.length; i++) {
            res = this.findElement(res, tags[i]);
            if (res == null)
                return null;
        }
        return res;
    };
    this.getBlob = function() {
        return new Blob([et.asXML()], {type: "text/xml;charset=utf8"});
    };
    this.forEach = function(obj, iterator, context) {
        angular.forEach(obj, function(v, k, o) {
            if (!v.attributes || !v.attributes.alt)
                iterator.call(context, v, k, o);
        });
    };
    this.findLdmlElement = function(base, tag) {
        if (base == null) {
            if (et == null)
                newET();
            base = et.root;
        }
        if (base.children == null)
            return null;
        for (var i = 0; i < base.children.length; i++) {
            if (base.children[i].tag == tag && !base.children[i].attributes.alt)
                return base.children[i];
        }
        return null;
    }
    return this;
  }])
  ;
