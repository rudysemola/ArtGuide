import { post } from "../utils"
import { AdaptationEndpoint } from "../environment"
import { ClassificationResult, QueryExpansionResponse, QueryBuildResult, PageResult } from "../models"
import { GoogleSearch } from "./google-search"
import { Parser } from "../parser"
import { logger } from "../logger"

/**
 * Perform web searches.
 */
export class Search {

  /** Google Search service */
  private googleSearch = new GoogleSearch()

  /** Parser */
  private parser = new Parser()

  /**
   * Builds a basic query basing on the Classification module result.
   * @param classificationResult The object received from the Classification module.
   * @returns {string} A basic query string.
   */
  private buildBasicQuery(classificationResult: ClassificationResult): string {
    // FIXME: return a meaningful query
    const query = classificationResult.classification.entities[0].description
    logger.silly('[search.ts] Basic query built: ', query)
    return query
  }


  /**
  * Extend a query by using the query expansion provided by the Adaptation module.
  * @param query A string representing basic query.
  * @param queryExpansion The query expansion provided by the Adaptation module.
  * @returns {Array<QueryBuildResult>} An array of object containing the originalQuery and an array expandedKeywords.
  */
  private extendQuery(query: string, queryExpansion: QueryExpansionResponse): Array<QueryBuildResult> {
    logger.silly('[search.ts] Query expansion: ', queryExpansion)
    const queries: Array<QueryBuildResult> = []

    Object.keys(queryExpansion.keywordExpansion).forEach(keyExpansion => {
      const keywords = queryExpansion.keywordExpansion[keyExpansion] as Array<string>
      queries.push({
        originalQuery: query,
        expandedKeywords: keywords
      })
    })
    logger.debug('[search.ts] Final queries: ', queries)

    return queries
  }


  /**
   * Build an array of queries using the query expansion provided by the Adaptation module.
   * @param classificationResult The object received from the Classification module.
   * @returns {Promise<Array<QueryBuildResult>>} A promise resolved with the array of queries of type QueryBuildResult.
   */
  private buildQuery(classificationResult: ClassificationResult): Promise<Array<QueryBuildResult>> {
    // build the basic query using the Classification result
    const basicQuery = this.buildBasicQuery(classificationResult)
    // get the query expansion from the Adaptation module
    return post<QueryExpansionResponse>(
      AdaptationEndpoint + "/keywords", classificationResult)
      // extend the basic query with the query expansion
      .then(queryExpansion => this.extendQuery(basicQuery, queryExpansion))
  }


  /**
   * Build a result object by querying Google Search the provided query.
   * @param queries The buildQuery result.
   * @returns {Array<PageResult>} An array of page result to be sent to the Adaptation module.
   */
  private buildResult(queries: QueryBuildResult[]): Promise<Array<PageResult>> {


    /*
      TODO:
        For each basic query (eg. "Leaning Tower of Pisa") we perform a Google Search for each 
        keywords that come from the adaptation group (eg. "Leaning Tower of Pisa Art", "Leaning Tower of Pisa Description", ecc).

        Each google search produces a set of pages that are actually merged regardless 
        the fact they they could potentially be duplicated.

        We need to merge duplicated results, taking into account that we have to find a way
        to merge their keywords and produce a a reasonable score index.
    */

    const results: Array<PageResult> = []

    return Promise.all(
      // for each query
      queries.map(async q => {
        // query Google Search and get the list of results
        return this.googleSearch.queryCustom(q.originalQuery + " " + q.expandedKeywords.join(" ")).then(queryResult => {
          
          if (queryResult.error) {
            const err = new Error(queryResult.error.message)
            logger.error('[search.ts] Query result error: ', err)
            throw err
          }
          
          return Promise.all(
            // for each result
            queryResult.items.map(item => {
              // Scrape text from results
              try {
                return this.parser.parse(item.link).then(parsedContent => {
                  parsedContent.keywords = q.expandedKeywords
                  results.push(parsedContent)
                  logger.silly('[search.ts] Parsed link ', item.link)
                })
              } catch (err) {
                // FIXME: fix the CSS error inside the parser
                logger.warn('[search.ts] Parser error: ', err, ". Link: ", item.link)
              }
            })
          )
        })
      })
    ).then(() => results)
  }


  /**
   * Perform a web search.
   * @param classificationResult The object received from the Classification module.
   * @returns {Promise<Array<PageResult>>} A list of page results.
   */
  public search(classificationResult: ClassificationResult): Promise<Array<PageResult>> {
    return this.buildQuery(classificationResult).then(q => this.buildResult(q))
  }

}