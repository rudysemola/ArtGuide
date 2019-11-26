/// <reference types="@types/jest"/>
/// <reference types="@types/node"/>


import fetch from "node-fetch";
import wikijs from "wikijs";

// eslint-disable-next-line
const wbk = require("wikidata-sdk");

enum WikidataPropertyType {
    InstanceOf = "P31",
    // Painting / statue
    Creator = "P170",
    Genre = "P136",
    Movement = "P135",
    // Monument
    Architect = "P84",
    ArchitecturalStyle = "P149",
    Painting = "Q3305213",
    Sculpture = "Q860861",
}


describe("Wikidata", () => {
    it("Should return simplified claims", async () => {

        const url = wbk.getEntities(["Q39054"]); // pisa tower

        const content = await fetch(url)
            .then(r => r.json());

        // simplify entities (https://github.com/maxlath/wikibase-sdk/blob/master/docs/simplify_entities_data.md#simplify-entities)
        content.entities = wbk.simplify.entities(content.entities);

        // contains the key of the enum => ["InstanceOf", "Creator", ...]
        const properties = Object.keys(WikidataPropertyType).filter(k => Number.isNaN(Number(k)));


        const simplifiedEntities: {
            [k: string]: Array<string>
        } = {};

        // for each entity id
        Object.keys(content.entities).forEach(entityId => {

            // for each property we want to extract
            properties.forEach(property => {
                const simplifiedClaimsForProperty = content.entities[entityId].claims[(WikidataPropertyType as any)[property]]
                simplifiedEntities[property] = simplifiedClaimsForProperty || [];
            });
        });

        console.log(simplifiedEntities)

        expect(simplifiedEntities.InstanceOf).toEqual(["Q200334", "Q570116"]);
        expect(simplifiedEntities.Painting).toEqual([]);

    });

    it("Should return Wikipedia name from Wikidata id", async () => {

        const wikidataId = "Q39054"; // pisa tower

        const url = wbk.getEntities([wikidataId]);

        const content = await fetch(url)
            .then(r => r.json());

        const lang = "en";

        const wikipediaPageTitle = content.entities[wikidataId].sitelinks[`${lang}wiki`].title

        const page = await wikijs().find(wikipediaPageTitle);

        expect(wikipediaPageTitle).toBe("Leaning Tower of Pisa");
    });
});