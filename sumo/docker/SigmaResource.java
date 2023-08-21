package com.articulate.sigma.rest;

/*
http://localhost:8080/sigmarest/resources/helloworld
 */
import javax.ws.rs.*;
import javax.ws.rs.core.Response;

import com.articulate.sigma.*;
import com.articulate.sigma.trans.TPTP3ProofProcessor;
import com.articulate.sigma.tp.Vampire;
import com.articulate.sigma.wordNet.*;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.*;

import org.json.simple.JSONAware;
import org.json.simple.JSONValue;

@Path("/")
public class SigmaResource {
    @Path("init")
    @GET
    public Response init() {
        KBmanager.getMgr().initializeOnce();
        try {
            KB kb = KBmanager.getMgr().getKB("SUMO");
        } catch (Exception e) {
            System.out.println(e.toString());
            return Response.serverError().entity(e.toString()).build();
        }
        return Response.ok("Sigma init completed").build();
    }

    @Path("reset")
    @GET
    public Response reset() {
        try {
            KB kb = KBmanager.getMgr().getKB("SUMO");
            kb.deleteUserAssertionsAndReload();
        } catch (Exception e) {
            System.out.println(e.toString());
            return Response.serverError().entity(e.toString()).build();
        }
        return Response.ok("Sigma reset completed").build();
    }

    @Path("ask")
    @GET
    @Produces("application/json")
    public Response query(
            @DefaultValue("(subclass ?X Object)") @QueryParam("query") String query,
            @DefaultValue("30") @QueryParam("timeout") int timeout) {
        KB kb = KBmanager.getMgr().getKB("SUMO");
        long start = System.currentTimeMillis();
        TPTP3ProofProcessor tpp = null;
        kb.loadVampire();
        Vampire vamp = kb.askVampire(query, timeout, 10);
        tpp = new TPTP3ProofProcessor();
        tpp.parseProofOutput(vamp.output, query, kb, vamp.qlist);
        long end = System.currentTimeMillis();
        double durationS = (end - start) / 1000.0;
        System.out.println(tpp.bindingMap);

        String tor = "{\"bindings\": " + this.toJSON(tpp.bindingMap)
                + ", \"proof\": " + this.toJSON(tpp.proof)
                + ", \"time\": " + durationS;
        if (durationS >= timeout) {
            tor += ", \"error\": \"timeout\"}";
            return Response.serverError().entity(tor).build();
        }
        tor += "}";
        return Response.ok(tor).build();
    }

    @Path("tell")
    @GET
    public Response tell(
            @DefaultValue("Object") @QueryParam("statement") String statement) {
        KB kb = KBmanager.getMgr().getKB("SUMO");
        String resp = kb.tell(statement);
        return Response.ok(resp).build();
    }

    @Path("term")
    @GET
    @Produces("application/json")
    public Response term(
            @DefaultValue("Object") @QueryParam("term") String term) {
        KB kb = KBmanager.getMgr().getKB("SUMO");
        if (!kb.containsTerm(term))
            return Response.serverError().entity("no such term in KB: " + term).build();
        Set<String> response = KBmanager.getMgr().getKB("SUMO").kbCache.getChildClasses(term);
        if (response == null)
            return Response.serverError().entity("no results for term: " + term).build();
        return Response.ok(this.toJSON(response)).build();
    }

    private String toJSON(Set<String> data) {
        String tor = "[";
        for (String d : data) {
            if (tor.length() > 1)
                tor += ", ";
            tor += d;
        }
        tor += "]";
        return tor;
    }

    private <T extends Object> String toJSON(List<T> data) {
        String tor = "[";
        for (T d : data) {
            if (tor.length() > 1)
                tor += ", ";
            tor += "\"" + d.toString() + "\"";
        }
        tor += "]";
        return tor;
    }

    private String toJSON(Map<String, String> data) {
        String tor = "{";
        for (Map.Entry<String, String> entry : data.entrySet()) {
            String key = entry.getKey();
            String value = entry.getValue();

            if (tor.length() > 1)
                tor += ", ";
            tor += "\"" + key + "\": " + "\"" + value + "\"";
        }
        tor += "}";
        return tor;
    }
}