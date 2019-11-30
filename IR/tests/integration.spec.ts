/// <reference types="@types/jest"/>

import request from 'supertest'
import app from "../src/app"
import nock from 'nock'
import { AdaptationEndpoint } from '../src/environment'
import classificationResult from "../assets/classification-result.json"
import queryExpansionResponse from "../assets/query-expansion-response.json"
import { UserProfile, PageResult } from '../src/models'



const adaptationKeywordUrl = new URL(AdaptationEndpoint.keywords);
nock(adaptationKeywordUrl.origin)
    .post(adaptationKeywordUrl.pathname)
    .reply((url, body: { userProfile: UserProfile }, callback) => {

        // verify passes parameters
        expect(body).not.toHaveProperty("classification");
        expect(body.userProfile).toBeDefined();

        // reply with 200 status code and the JSON response
        callback(null, [
            200,
            queryExpansionResponse
        ]);
    });

const adaptationTextUrl = new URL(AdaptationEndpoint.text);
nock(adaptationTextUrl.origin)
    .post(adaptationTextUrl.pathname)
    .reply((url, body: { userProfile: UserProfile, results: Array<PageResult> }, callback) => {

        // verify passes parameters
        expect(body).not.toHaveProperty("classification");
        expect(body.userProfile).toBeDefined();
        expect(body.results).toBeDefined();

        // reply with 200 status code and a mock JSON response
        callback(null, [
            200,
            { message: "Mock" }
        ]);
    });

describe("Integration tests", () => {

    it("Should respond properly", () => {
        return request(app)
            .post("/")
            .send(classificationResult)
            .then(response => {
                expect(response.status).toEqual(200)
                expect(response.body.message).toEqual('Mock')
            })
    })

})